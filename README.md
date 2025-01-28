# dxf2geojson
dxf2geojson.exeは、Potree などのソフトウェアで作成した平面直角座標系の3次元ポリゴンを、DXF形式からgeojson形式に変換するためのプログラムです。出力座標系は、WGS84（EPSG4326）、Webメルカトル（EPSG3857）又は平面直角座標系（EPSG6677ほか）の中から選択できます。

# 使用方法
## プログラムの準備
dxf2geojson.exe をダウンロードしてデスクトップなど、分かりやすい場所に保存します（インストールは不要です）。
![スクリーンショット 2024-12-16 191628](https://github.com/user-attachments/assets/162b2f6d-4a9e-4540-82e4-43504c117d53)


## 3次元ポリゴンデータの作成（例として PotreeDesktop）
平面直角座標系で作成された点群（LAS/LAZ）をPotreeDesktopに読み込みます。
PotreeDesktopで3次元ポリゴンを作成し、DXFファイルとして出力します。
![スクリーンショット 2024-12-16 181831](https://github.com/user-attachments/assets/c6c93b26-b3fb-46c0-b281-66d0bd02d09c)

## DXFファイルの変換
出力したDXFファイルを dxf2geojson.exe にドラッグ＆ドロップします。
表示されたダイアログで、対応するEPSGコードを選択します（例: 茨城県 = EPSG:6677）。
「OK」ボタンを押します。
![スクリーンショット 2024-12-16 183105](https://github.com/user-attachments/assets/5fdc5333-ccc1-4018-9c14-2fbbd1f3830f)


## 変換後のgeojsonファイル
dxfファイルと同じディレクトリに、geojson形式 に変換された3次元ポリゴンデータが保存されます。
QGIなど一般的なGISソフトウェアで読込・表示が可能です。
![スクリーンショット 2024-12-16 183854](https://github.com/user-attachments/assets/c10190c6-105f-4085-9752-fa1de4f75b52)
