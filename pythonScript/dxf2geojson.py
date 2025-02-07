"""
DXF to GeoJSON Converter (JGD2011 to Web Mercator)
Version: 1.2
License: MIT
"""

import os
import sys
import logging
import datetime
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from typing import List, Dict, Any, Optional
import time
import math

import ezdxf
from ezdxf.document import Drawing
from ezdxf.entities import DXFEntity
import geopandas as gpd
from shapely.geometry import Point, LineString, Polygon, MultiPolygon, shape
from shapely.ops import orient
from pyproj import Transformer
import geojson
import json
from shapely.geometry import mapping

# 定数定義
DEFAULT_EPSG = 6677  # 東京を含む第9系
OUTPUT_CRS_OPTIONS = {
    "Web Mercator (EPSG:3857)": "EPSG:3857",
    "WGS84 (EPSG:4326)": "EPSG:4326"
}
SUPPORTED_ENTITIES = {"POINT", "LWPOLYLINE", "POLYLINE", "CIRCLE", "ARC", "LINE"}

#########################
# ログ設定
#########################
def setup_logging() -> None:
    """ログ設定"""
    try:
        # 実行ファイルのパスを取得
        if getattr(sys, 'frozen', False):
            app_path = os.path.dirname(sys.executable)
        else:
            app_path = os.path.dirname(os.path.abspath(__file__))
        
        # ログディレクトリを実行ファイルと同じ場所に設定
        log_dir = os.path.join(app_path, 'logs')
        os.makedirs(log_dir, exist_ok=True)

        current_time = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        log_file = os.path.join(log_dir, f'dxf2geojson_{current_time}.log')

        # ログハンドラーの設定
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        console_handler = logging.StreamHandler(sys.stdout)
        
        # フォーマッターの設定
        formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        # ルートロガーの設定
        logger = logging.getLogger()
        logger.setLevel(logging.INFO)
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
        
        logging.info("=== DXF to GeoJSON Converter ===")
        logging.info(f"ログファイル: {log_file}")
        
    except Exception as e:
        print(f"ログ設定エラー: {str(e)}")
        sys.exit(1)

#########################
# EPSG選択ダイアログ
#########################
class EPSGSelector:
    """平面直角座標系選択用GUI"""
    
    EPSG_OPTIONS = {
        1: (6669, "長崎県、鹿児島県の一部"),
        2: (6670, "福岡県、佐賀県、熊本県、大分県、宮崎県、鹿児島県の一部"),
        3: (6671, "山口県、島根県、広島県"),
        4: (6672, "香川県、愛媛県、徳島県、高知県"),
        5: (6673, "兵庫県、鳥取県、岡山県"),
        6: (6674, "京都府、大阪府、福井県、滋賀県、三重県、奈良県、和歌山県"),
        7: (6675, "石川県、富山県、岐阜県、愛知県"),
        8: (6676, "新潟県、長野県、山梨県、静岡県"),
        9: (6677, "東京都、福島県、栃木県、茨城県、埼玉県、千葉県、群馬県、神奈川県"),
        10: (6678, "青森県、秋田県、山形県、岩手県、宮城県"),
        11: (6679, "北海道の一部（小樽市、函館市など）"),
        12: (6680, "北海道の一部"),
        13: (6681, "北海道の一部（北見市、帯広市など）"),
        14: (6682, "東京都の一部（南方諸島）"),
        15: (6683, "沖縄県の一部"),
        16: (6684, "沖縄県の一部"),
        17: (6685, "沖縄県の一部"),
        18: (6686, "東京都の一部（南方諸島）"),
        19: (6687, "東京都の一部（南方諸島）")
    }

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("座標系選択")
        self.selected_epsg = DEFAULT_EPSG
        self._setup_ui()

    def _setup_ui(self) -> None:
        """GUIコンポーネントの初期化"""
        frame = ttk.Frame(self.root, padding=10)
        frame.grid(row=0, column=0, sticky=tk.NSEW)

        label = ttk.Label(frame, text="DXFファイルの平面直角座標系を選択してください:")
        label.grid(row=0, column=0, sticky=tk.W, pady=5)

        # 表示用の選択肢を作成
        options = [f"第{code}系: {desc}" for code, (_, desc) in self.EPSG_OPTIONS.items()]
        self.combo_var = tk.StringVar(value=options[8])  # デフォルト第9系
        combo = ttk.Combobox(frame, textvariable=self.combo_var, values=options, 
                           state="readonly", width=60)
        combo.grid(row=1, column=0, padx=5, pady=5)

        ttk.Button(frame, text="OK", command=self._on_ok).grid(row=2, column=0, pady=10)

    def _on_ok(self) -> None:
        """OKボタン処理"""
        selected = self.combo_var.get()
        # "第X系: 説明" から系番号を取得
        system_number = int(selected.split("第")[1].split("系")[0])
        self.selected_epsg = self.EPSG_OPTIONS[system_number][0]  # EPSGコードを取得
        self.root.destroy()

    def get_epsg(self) -> int:
        """選択されたEPSGコードを取得"""
        self.root.mainloop()
        return self.selected_epsg

#########################
# 出力座標系選択ダイアログ
#########################
class OutputCRSSelector:
    """出力座標系選択ダイアログ"""
    
    def __init__(self, input_epsg: str):
        self.input_epsg = input_epsg
        self.crs_options = {
            "WGS84 (EPSG:4326)": "EPSG:4326",
            "Web Mercator (EPSG:3857)": "EPSG:3857",
            f"入力座標系 (EPSG:{input_epsg})": f"EPSG:{input_epsg}"
        }
        self.default_crs = "EPSG:4326"

    def get_crs(self) -> str:
        # メインウィンドウ作成
        root = tk.Tk()
        root.title("出力座標系の選択")
        root.geometry("300x200")

        selected_crs = tk.StringVar(value=self.default_crs)

        # ラジオボタン作成
        label = tk.Label(root, text="出力座標系を選択してください：")
        label.pack(pady=10)

        for text, crs in self.crs_options.items():
            rb = tk.Radiobutton(
                root,
                text=text,
                value=crs,
                variable=selected_crs
            )
            rb.pack(anchor=tk.W, padx=20)

        # OKボタン
        ok_button = tk.Button(
            root,
            text="OK",
            command=root.quit
        )
        ok_button.pack(pady=10)

        # ウィンドウを中央に配置
        root.update_idletasks()
        width = root.winfo_width()
        height = root.winfo_height()
        x = (root.winfo_screenwidth() // 2) - (width // 2)
        y = (root.winfo_screenheight() // 2) - (height // 2)
        root.geometry(f"{width}x{height}+{x}+{y}")

        # メインループ
        root.mainloop()
        
        selected = selected_crs.get()
        root.destroy()
        
        return selected

#########################
# DXF処理モジュール
#########################
class DXFProcessor:
    """DXFファイルの読み込みとジオメトリ変換"""
    
    def __init__(self, dxf_path: str):
        self.dxf_path = dxf_path
        self.doc: Drawing = ezdxf.readfile(dxf_path)
        self.msp = self.doc.modelspace()
        self.features: List[Dict[str, Any]] = []

    def _process_entity(self, entity: DXFEntity) -> None:
        """個々のDXFエンティティを処理"""
        try:
            dxftype = entity.dxftype()
            if dxftype not in SUPPORTED_ENTITIES:
                return

            geom = None
            prop = {
                "layer": entity.dxf.layer,
                "color": entity.dxf.color,
                "dxftype": dxftype
            }

            if dxftype == "POINT":
                geom = self._extract_point(entity)
                if geom:
                    self.features.append({
                        "type": "Feature",
                        "geometry": mapping(geom),
                        "properties": prop
                    })
            elif dxftype in {"LWPOLYLINE", "POLYLINE"}:
                feature = self._extract_polyline(entity)
                if feature:
                    self.features.append(feature)
            elif dxftype == "LINE":
                geom = self._extract_line(entity)
                if geom:
                    self.features.append({
                        "type": "Feature",
                        "geometry": mapping(geom),
                        "properties": prop
                    })
            elif dxftype in {"CIRCLE", "ARC"}:
                feature = self._extract_curve(entity)
                if feature:
                    self.features.append(feature)

        except Exception as e:
            logging.error(f"エンティティ処理エラー: {str(e)}")

    def _extract_point(self, entity) -> Point:
        """POINTエンティティの抽出"""
        loc = entity.dxf.location
        return Point(loc.x, loc.y, loc.z)

    def _extract_polyline(self, entity) -> Optional[Dict[str, Any]]:
        """POLYLINE/LWPOLYLINE処理"""
        try:
            coords_3d = []
            dxftype = entity.dxftype()
            logging.info(f"[高さ追跡] 処理開始: エンティティタイプ = {dxftype}")

            # エンティティの基準高さを取得
            base_elevation = 0.0
            if hasattr(entity.dxf, 'elevation'):
                if isinstance(entity.dxf.elevation, (int, float)):
                    base_elevation = float(entity.dxf.elevation)
                elif hasattr(entity.dxf.elevation, 'z'):
                    base_elevation = float(entity.dxf.elevation.z)
                elif isinstance(entity.dxf.elevation, (list, tuple)):
                    base_elevation = float(entity.dxf.elevation[2])  # Z座標を取得
            logging.info(f"[高さ追跡] 基準高さ: {base_elevation}")

            # POLYLINE/LWPOLYLINEの処理
            if dxftype == "LWPOLYLINE":
                for point in entity.get_points():
                    x, y = point[:2]
                    # 高さ情報を取得（bulge情報がある場合は除外）
                    z = point[2] if len(point) > 2 and not isinstance(point[2], (bool, int)) else base_elevation
                    coords_3d.append([float(x), float(y), float(z)])
                    logging.info(f"[高さ追跡] LWPOLYLINE頂点: x={x}, y={y}, z={z}")
            
            elif dxftype == "POLYLINE":
                for vertex in entity.vertices:
                    if not hasattr(vertex.dxf, 'location'):
                        continue
                    loc = vertex.dxf.location
                    x = float(loc.x)
                    y = float(loc.y)
                    # Z座標の取得を試みる（複数の方法）
                    if hasattr(loc, 'z'):
                        z = float(loc.z)
                    elif hasattr(vertex.dxf, 'elevation'):
                        z = float(vertex.dxf.elevation)
                    else:
                        z = base_elevation
                    coords_3d.append([x, y, z])
                    logging.info(f"[高さ追跡] POLYLINE頂点: x={x}, y={y}, z={z}")

            if not coords_3d:
                logging.warning(f"[高さ追跡] 有効な座標が取得できませんでした: {dxftype}")
                return None

            # 重複頂点の除去（数値誤差を考慮）
            unique_coords = []
            for coord in coords_3d:
                if not unique_coords or not all(abs(a - b) < 1e-8 for a, b in zip(coord, unique_coords[-1])):
                    unique_coords.append(coord)

            # ポリゴンクローズの処理
            is_closed = False
            if hasattr(entity.dxf, 'flags'):
                is_closed = bool(entity.dxf.flags & 1)
            elif hasattr(entity, 'closed'):
                is_closed = entity.closed

            if is_closed and len(unique_coords) >= 3:
                if not all(abs(a - b) < 1e-8 for a, b in zip(unique_coords[0], unique_coords[-1])):
                    unique_coords.append(unique_coords[0].copy())

            # 高さの統計情報を計算
            z_values = [coord[2] for coord in unique_coords]
            z_stats = {
                "min_z": min(z_values),
                "max_z": max(z_values),
                "avg_z": sum(z_values) / len(z_values)
            }
            
            # GeoJSON Feature の作成
            feature = {
                "type": "Feature",
                "geometry": {
                    "type": "Polygon" if is_closed and len(unique_coords) >= 4 else "LineString",
                    "coordinates": [unique_coords] if is_closed and len(unique_coords) >= 4 else unique_coords
                },
                "properties": {
                    "layer": str(entity.dxf.layer),
                    "color": int(entity.dxf.color),
                    "dxftype": str(dxftype),
                    "elevation": base_elevation,
                    **z_stats
                }
            }

            logging.info(f"[高さ追跡] フィーチャ作成完了: {z_stats}")
            return feature

        except Exception as e:
            logging.error(f"[高さ追跡] ポリライン処理エラー: {str(e)}")
            import traceback
            logging.error(traceback.format_exc())
            return None

    def _extract_line(self, entity) -> LineString:
        """LINEエンティティ処理"""
        start = entity.dxf.start
        end = entity.dxf.end
        return LineString([(start.x, start.y, start.z), (end.x, end.y, end.z)])

    def _extract_curve(self, entity) -> Optional[Dict[str, Any]]:
        """CIRCLE/ARCエンティティの処理"""
        try:
            dxftype = entity.dxftype()
            center = entity.dxf.center
            radius = entity.dxf.radius
            
            if dxftype == "CIRCLE":
                # 円を近似する点の数（精度）
                num_points = 32
                points = []
                for i in range(num_points + 1):
                    angle = (i * 2 * math.pi) / num_points
                    x = center.x + radius * math.cos(angle)
                    y = center.y + radius * math.sin(angle)
                    z = center.z
                    points.append([x, y, z])
                
                return {
                    "type": "Feature",
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [points]
                    },
                    "properties": {
                        "layer": str(entity.dxf.layer),
                        "color": int(entity.dxf.color),
                        "dxftype": str(dxftype),
                        "radius": radius
                    }
                }
                
            elif dxftype == "ARC":
                start_angle = math.radians(entity.dxf.start_angle)
                end_angle = math.radians(entity.dxf.end_angle)
                
                # 終了角度が開始角度より小さい場合、360度を加算
                if end_angle < start_angle:
                    end_angle += 2 * math.pi
                    
                # 円弧を近似する点の数（精度）
                num_points = 16
                points = []
                
                for i in range(num_points + 1):
                    angle = start_angle + (i * (end_angle - start_angle)) / num_points
                    x = center.x + radius * math.cos(angle)
                    y = center.y + radius * math.sin(angle)
                    z = center.z
                    points.append([x, y, z])
                
                return {
                    "type": "Feature",
                    "geometry": {
                        "type": "LineString",
                        "coordinates": points
                    },
                    "properties": {
                        "layer": str(entity.dxf.layer),
                        "color": int(entity.dxf.color),
                        "dxftype": str(dxftype),
                        "radius": radius,
                        "start_angle": entity.dxf.start_angle,
                        "end_angle": entity.dxf.end_angle
                    }
                }
                
        except Exception as e:
            logging.error(f"円/円弧の処理エラー: {str(e)}")
            return None

    def process(self) -> List[Dict[str, Any]]:
        """全エンティティの処理"""
        logging.info(f"DXF処理開始: {self.dxf_path}")
        for entity in self.msp:
            self._process_entity(entity)
        logging.info(f"抽出ジオメトリ数: {len(self.features)}")
        return self.features

#########################
# 座標変換モジュール
#########################
class CoordinateTransformer:
    """座標変換処理を管理"""
    
    def __init__(self, src_epsg: int, dst_crs: str):
        self.src_epsg = src_epsg
        self.transformer = Transformer.from_crs(
            f"EPSG:{src_epsg}", 
            dst_crs, 
            always_xy=True
        )

    def transform_geometry(self, feature: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """GeoJSON形式のジオメトリを変換"""
        try:
            if not feature or "geometry" not in feature:
                return None

            coords = feature["geometry"]["coordinates"]
            geom_type = feature["geometry"]["type"]
            
            if geom_type == "Polygon":
                transformed_coords = []
                for ring in coords:
                    transformed_ring = []
                    for coord in ring:
                        if len(coord) != 3:
                            continue
                        x, y, z = coord
                        new_x, new_y = self.transformer.transform(x, y)
                        transformed_ring.append([new_x, new_y, z])  # Z座標を保持
                    transformed_coords.append(transformed_ring)
                feature["geometry"]["coordinates"] = transformed_coords
                
            elif geom_type == "LineString":
                transformed_coords = []
                for coord in coords:
                    if len(coord) != 3:
                        continue
                    x, y, z = coord
                    new_x, new_y = self.transformer.transform(x, y)
                    transformed_coords.append([new_x, new_y, z])  # Z座標を保持
                feature["geometry"]["coordinates"] = transformed_coords
            
            return feature
            
        except Exception as e:
            logging.error(f"座標変換エラー: {str(e)}")
            return None

#########################
# メイン処理
#########################
def process_geometry(geometry):
    """ジオメトリの向きを修正"""
    if isinstance(geometry, Polygon):
        # 外側の輪を反時計回りに修正
        coords = list(geometry.exterior.coords)
        coords.reverse()
        return Polygon(coords)
    return geometry

def process_dxf_file(dxf_path: str, epsg: int, output_crs: str) -> None:
    """DXFファイルを処理"""
    try:
        processor = DXFProcessor(dxf_path)
        features = processor.process()
        
        if not features:
            logging.warning("変換可能なジオメトリが見つかりませんでした")
            return
            
        # 座標変換
        transformer = CoordinateTransformer(epsg, output_crs)
        transformed_features = []
        for feature in features:
            transformed_feature = transformer.transform_geometry(feature)
            if transformed_feature:
                transformed_features.append(transformed_feature)
        
        # GeoJSONファイル作成
        output_path = dxf_path.rsplit('.', 1)[0] + f'_epsg{output_crs.split(":")[-1]}.geojson'
        
        # GeoJSON形式で保存
        geojson_data = {
            "type": "FeatureCollection",
            "features": transformed_features,
            "crs": {
                "type": "name",
                "properties": {
                    "name": output_crs
                }
            }
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(geojson_data, f, ensure_ascii=False, indent=2)
            
        logging.info(f"出力完了: {output_path}")
        
    except Exception as e:
        logging.error(f"ファイル処理エラー: {dxf_path} - {str(e)}")
        raise

def main():
    try:
        setup_logging()
        
        # コマンドライン引数の取得とチェック
        dxf_files = sys.argv[1:] if len(sys.argv) > 1 else []
        
        if not dxf_files:
            # GUIモード
            root = tk.Tk()
            root.withdraw()
            dxf_files = filedialog.askopenfilenames(
                title="DXFファイルを選択",
                filetypes=[("DXF files", "*.dxf"), ("All files", "*.*")]
            )
            root.destroy()
        
        if not dxf_files:
            logging.error("ファイルが選択されませんでした")
            messagebox.showwarning("警告", "ファイルが選択されませんでした")
            return

        # 入力ファイルの存在確認
        for dxf_path in dxf_files:
            if not os.path.isfile(dxf_path):
                raise FileNotFoundError(f"ファイルが見つかりません: {dxf_path}")
        
        # 入力座標系の選択
        epsg = EPSGSelector().get_epsg()
        logging.info(f"選択座標系: EPSG:{epsg}")

        # 出力座標系の選択
        output_crs = OutputCRSSelector(epsg).get_crs()
        logging.info(f"出力座標系: {output_crs}")

        # 各ファイルを処理
        for dxf_path in dxf_files:
            process_dxf_file(dxf_path, epsg, output_crs)
            
        logging.info("すべての処理が完了しました")
        messagebox.showinfo("完了", "すべての処理が完了しました")
        
    except Exception as e:
        logging.critical(f"致命的エラー: {str(e)}", exc_info=True)
        messagebox.showerror("エラー", str(e))

if __name__ == "__main__":
    main()
