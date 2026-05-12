/*************************************************************************/
/*                                                                       */
/*  mnb_bmp.h: PBL画像シミュレーション ライブラリのためのヘッダファイル            */
/*                                                                       */
/*                       Hiroyuki Manabe                                 */
/*                                                                       */
/*         Kazutoshi Ando (Shizuoka Univ.) 先生のプログラムを真鍋が改変       */
/*************************************************************************/
#ifndef MNB_BMP_H
#define MNB_BMP_H

#define HEADERSIZE   54               /* ヘッダのサイズ 54 = 14 + 40         */
#define PALLETSIZE 1024               /* パレットのサイズ                    */

#define PIXEL_WIDTH		5
#define LINE_WIDTH		2
#define SCALE_LENGTH	2

#define MAXWIDTH   1000              /* 最大の幅(pixel)          */
#define MAXHEIGHT  1000              /* 最大の高さ(pixel)        */

//ピクセルの赤緑青の各輝度
typedef struct {
    unsigned char r;
    unsigned char g;
    unsigned char b;
} color;

typedef struct {
    long height;
    long width;
    color **data;
} img;

//出力中の仮想LEDディスプレイ
extern img *bmp_img;

//仮想LEDディスプレイに出力する前の輝度情報
extern color **img_canvas;

//仮想LEDディスプレイのLED行数
extern int _panel_rows;

//仮想LEDディスプレイのLED列数
extern int _panel_cols;

//LEDディスプレイの動画を書出すかどうかのフラグ
//デフォルトは0(書出す)
extern int disable_recording;

//disable_recording=1 の時に静止画が出力されるパス
extern char log_image_path[32];

//静止画を出力した回数
extern int still_image_count;

//動画書出しのfps　デフォルトは30
extern int recording_fps;
/*
   関数名: ReadBmp
   引数  : char *filename, img *imgp
   返り値: void
   動作  : bmp形式のファイル filename を開いて, その画像データを
           2次元配列 imgp->data に格納する. 同時に, ヘッダから読み込まれた
           画像の幅と高さをグローバル変数 Bmp_width とBmp_height にセットする.
*/
void ReadBmp(char *filename, img *imgp);

/*
   関数名: WriteBmp
   引数  : char *filename, img *tp
   返り値: void
   動作  : 2次元配列 tp->data の内容を画像データとして, 24ビット
           bmp形式のファイル filename に書き出す.
*/
void WriteBmp(char *filename, img *tp);

/*
lineclr1：全てのピクセルを区切る線の色
lineclr2：5の倍数の時に区切る色の線
lineclr3：10の倍数の時に区切る線
*/
void drawGrid(color lineclr1, color lineclr2, color lineclr3);

/*
  set panel size
  if param is <=0 , size is 64 * 64
*/
void setPanelSize(int rows, int cols);

/*
  img_bmp offscreen_bmp　の初期化
*/
void initBmpImg();

/*
  一定時間ごとに imb_bmpをビットマップ画像に書き出し
*/
void takeTimelapse();

/*
  img_ptrの初期化関連
*/
void initBmpImage( img *img_ptr, int width, int height);
void freeBmpImage( img *img_ptr);
void ReadBmp2(char *filename, img *imgp);

#endif	//MNB_BMP_H
