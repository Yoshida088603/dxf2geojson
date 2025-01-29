# dxf2geojson
dxf2geojson.exeは、Potree などのソフトウェアで作成した平面直角座標系の3次元ポリゴンを、DXF形式からgeojson形式に変換するためのプログラムです。出力座標系は、WGS84（EPSG4326）、Webメルカトル（EPSG3857）又は平面直角座標系（EPSG6677ほか）の中から選択できます。

# 使用方法
## プログラムの準備
dxf2geojson.exe をダウンロードしてデスクトップなど、分かりやすい場所に保存します（インストール不要）。
<img width="761" alt="Download" src="https://github.com/user-attachments/assets/992cbb37-eedd-428c-80aa-11578de0c69f" />


## 3次元ポリゴンデータの作成（例として PotreeDesktop）
平面直角座標系で作成された点群（LAS/LAZ）をPotreeDesktopに読み込みます。
PotreeDesktopで3次元ポリゴンを作成し、DXFファイルとして出力します。
![potree](https://github.com/user-attachments/assets/8535c3cd-20be-4f56-9db3-e5177cbe5f43)


## DXFファイルの変換
出力したDXFファイルを dxf2geojson.exe にドラッグ＆ドロップします。
表示されたダイアログで、インポートとエクスポートのオプションを選択します（例: 入力ファイルオプション = 茨城県:EPSG 6677, 出力ファイルオプション = WGS84:EPSG 4326）。
![exportOption](https://github.com/user-attachments/assets/193f2b7d-3bd3-465e-b93b-3e6a2d3aa70d)
<img width="504" alt="importOption" src="https://github.com/user-attachments/assets/844bf7eb-a155-4d64-b0f6-68a365e8af3d" />


## 変換後のgeojsonファイル
dxfファイルと同じディレクトリに、geojson形式 に変換された3次元ポリゴンデータが保存されます。
QGIなど一般的なGISソフトウェアで読込・表示が可能です。
![qgis](https://github.com/user-attachments/assets/37b29526-0bca-4de3-99b1-8d6f3c0c3a74)

