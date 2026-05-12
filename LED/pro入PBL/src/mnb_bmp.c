/*************************************************************************/
/*                                                                       */
/*  mnb_bmp.h: PBL画像シミュレーション ライブラリのためのヘッダファイル            */
/*                                                                       */
/*                       Hiroyuki Manabe                                 */
/*                                                                       */
/*         Kazutoshi Ando (Shizuoka Univ.) 先生のプログラムを真鍋が改変       */
/*************************************************************************/
#include "mnb_bmp.h"
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <unistd.h>
#include <sys/stat.h>

img *bmp_img;
color **img_canvas;
int _panel_rows, _panel_cols;
int disable_recording = 0;
char log_image_path[32];
int still_image_count = 0;
int recording_fps = 30;


void ReadBmp(char *filename, img *imgp)
{
    int i, j;
    int Real_width;
    FILE *Bmp_Fp = fopen(filename, "rb");  /* バイナリモード読み込み用にオープン  */
    unsigned char *Bmp_Data;           /* 画像データを1行分格納               */


    unsigned char Bmp_headbuf[HEADERSIZE];/* ヘッダを格納するための変数          */
    char Bmp_type[2];                     /* ファイルタイプ "BM"                 */
    // long Bmp_height;                      /* 高さ (ピクセル)                     */
    // long Bmp_width;                       /* 幅   (ピクセル)                     */
    unsigned short Bmp_color;          /* 色 (ビット)     24                  */


    if (Bmp_Fp == NULL) {
        fprintf(stderr, "Error: file %s couldn\'t open for read!.\n", filename);
        exit(1);
    }

    /* ヘッダ読み込み */
    if(!fread(Bmp_headbuf, sizeof(unsigned char), HEADERSIZE, Bmp_Fp)) {
        fprintf(stderr, "Error: could not header.\n");
        exit(1);
    };

    memcpy(&Bmp_type, Bmp_headbuf, sizeof(Bmp_type));
    if (strncmp(Bmp_type, "BM", 2) != 0) {
        fprintf(stderr, "Error: %s is not a bmp file.\n", filename);
        exit(1);
    }

    memcpy(&imgp->width, Bmp_headbuf + 18, 4);//sizeof(Bmp_width));
    memcpy(&imgp->height, Bmp_headbuf + 22, 4);//sizeof(Bmp_height));
    memcpy(&Bmp_color, Bmp_headbuf + 28, sizeof(Bmp_color));

    printf("\nwidth:%ld\n", imgp->width);
    printf("height:%ld\n", imgp->height);

    if (Bmp_color != 24) {
        fprintf(stderr, "Error: Bmp_color = %d is not implemented in this program.\n", Bmp_color);
        exit(1);
    }

    if (imgp->width > MAXWIDTH) {
        fprintf(stderr, "Error: Bmp_width = %ld > %d = MAXWIDTH!\n", imgp->width, MAXWIDTH);
        exit(1);
    }

    if (imgp->height > MAXHEIGHT) {
        fprintf(stderr, "Error: Bmp_height = %ld > %d = MAXHEIGHT!\n", imgp->height, MAXHEIGHT);
        exit(1);
    }

    Real_width = imgp->width * 3 + imgp->width % 4; /* 4byte 境界にあわせるために実際の幅の計算 */

   /* 配列領域の動的確保. 失敗した場合はエラーメッセージを出力して終了 */
    if ((Bmp_Data = (unsigned char *)calloc(Real_width, sizeof(unsigned char))) == NULL) {
        fprintf(stderr, "Error: Memory allocation failed for Bmp_Data!\n");
        exit(1);
    }


    /* 画像データ読み込み */
    for (i = 0; i < imgp->height; i++) {
        if(!fread(Bmp_Data, 1, Real_width, Bmp_Fp)) {
            fprintf(stderr, "Error: could not header.\n");
            exit(1);
        }
        for (j = 0; j < imgp->width; j++) {
            imgp->data[imgp->height - i - 1][j].b = Bmp_Data[j * 3];
            imgp->data[imgp->height - i - 1][j].g = Bmp_Data[j * 3 + 1];
            imgp->data[imgp->height - i - 1][j].r = Bmp_Data[j * 3 + 2];
        }
    }


    /* 動的に確保した配列領域の解放 */
    free(Bmp_Data);

    /* ファイルクローズ */
    fclose(Bmp_Fp);
}

void ReadBmp2(char *filename, img *imgp)
{
    int i, j;
    int Real_width;
    FILE *Bmp_Fp = fopen(filename, "rb");  /* バイナリモード読み込み用にオープン  */
    unsigned char *Bmp_Data;           /* 画像データを1行分格納               */

    freeBmpImage( imgp);

    unsigned char Bmp_headbuf[HEADERSIZE];/* ヘッダを格納するための変数          */
    char Bmp_type[2];                     /* ファイルタイプ "BM"                 */
    // long Bmp_height;                      /* 高さ (ピクセル)                     */
    // long Bmp_width;                       /* 幅   (ピクセル)                     */
    unsigned short Bmp_color;          /* 色 (ビット)     24                  */


    if (Bmp_Fp == NULL) {
        fprintf(stderr, "Error: file %s couldn\'t open for read!.\n", filename);
        exit(1);
    }

    /* ヘッダ読み込み */
    if(!fread(Bmp_headbuf, sizeof(unsigned char), HEADERSIZE, Bmp_Fp)) {
        fprintf(stderr, "Error: could not header.\n");
        exit(1);
    };

    memcpy(&Bmp_type, Bmp_headbuf, sizeof(Bmp_type));
    if (strncmp(Bmp_type, "BM", 2) != 0) {
        fprintf(stderr, "Error: %s is not a bmp file.\n", filename);
        exit(1);
    }


    memcpy(&imgp->width, Bmp_headbuf + 18, 4);//sizeof(Bmp_width));
    memcpy(&imgp->height, Bmp_headbuf + 22, 4);//sizeof(Bmp_height));
    memcpy(&Bmp_color, Bmp_headbuf + 28, sizeof(Bmp_color));

    printf("\nwidth:%ld\n", imgp->width);
    printf("height:%ld\n", imgp->height);

    if (Bmp_color != 24) {
        fprintf(stderr, "Error: Bmp_color = %d is not implemented in this program.\n", Bmp_color);
        exit(1);
    }

    if (imgp->width > MAXWIDTH) {
        fprintf(stderr, "Error: Bmp_width = %ld > %d = MAXWIDTH!\n", imgp->width, MAXWIDTH);
        exit(1);
    }

    if (imgp->height > MAXHEIGHT) {
        fprintf(stderr, "Error: Bmp_height = %ld > %d = MAXHEIGHT!\n", imgp->height, MAXHEIGHT);
        exit(1);
    }

    initBmpImage( imgp, imgp->width, imgp->height);

    Real_width = imgp->width * 3 + imgp->width % 4; /* 4byte 境界にあわせるために実際の幅の計算 */

   /* 配列領域の動的確保. 失敗した場合はエラーメッセージを出力して終了 */
    if ((Bmp_Data = (unsigned char *)calloc(Real_width, sizeof(unsigned char))) == NULL) {
        fprintf(stderr, "Error: Memory allocation failed for Bmp_Data!\n");
        exit(1);
    }


    /* 画像データ読み込み */
    for (i = 0; i < imgp->height; i++) {
        if(!fread(Bmp_Data, 1, Real_width, Bmp_Fp)) {
            fprintf(stderr, "Error: could not header.\n");
            exit(1);
        }
        for (j = 0; j < imgp->width; j++) {
            imgp->data[imgp->height - i - 1][j].b = Bmp_Data[j * 3];
            imgp->data[imgp->height - i - 1][j].g = Bmp_Data[j * 3 + 1];
            imgp->data[imgp->height - i - 1][j].r = Bmp_Data[j * 3 + 2];
        }
    }


    /* 動的に確保した配列領域の解放 */
    free(Bmp_Data);

    /* ファイルクローズ */
    fclose(Bmp_Fp);
}


void WriteBmp(char *filename, img *tp)
{
    int i, j;
    int Real_width;
    FILE *Out_Fp = fopen(filename, "wb");   /* ファイルオープン                     */
    unsigned char *Bmp_Data;                /* 画像データを1行分格納                 */

    unsigned char Bmp_headbuf[HEADERSIZE];  /* ヘッダを格納するための変数             */

    unsigned long Bmp_size;                 /* bmpファイルのサイズ (バイト)          */
    unsigned int Bmp_info_header_size;      /* 情報ヘッダのサイズ = 40              */
    unsigned int Bmp_header_size;           /* ヘッダサイズ = 54                   */
    long Bmp_height;                        /* 高さ (ピクセル)                     */
    long Bmp_width;                         /* 幅   (ピクセル)                     */
    unsigned short Bmp_planes;              /* プレーン数 常に 1                    */
    unsigned short Bmp_color;               /* 色 (ビット)     24                  */
    long Bmp_image_size;                    /* 画像部分のファイルサイズ (バイト)       */
    long Bmp_xppm;                          /* 水平解像度 (ppm)                    */
    long Bmp_yppm;                          /* 垂直解像度 (ppm)                    */

    if (Out_Fp == NULL) {
        fprintf(stderr, "Error: file %s couldn\'t open for write!\n", filename);
        exit(1);
    }

    Bmp_color = 24;
    Bmp_header_size = HEADERSIZE;
    Bmp_info_header_size = 40;
    Bmp_planes = 1;

    Real_width = tp->width * 3 + tp->width % 4;  /* 4byte 境界にあわせるために実際の幅の計算 */

    /* 配列領域の動的確保. 失敗した場合はエラーメッセージを出力して終了 */
    if ((Bmp_Data = (unsigned char *)calloc(Real_width, sizeof(unsigned char))) == NULL) {
        fprintf(stderr, "Error: Memory allocation failed for Bmp_Data!\n");
        exit(1);
    }

    /* ヘッダ情報の準備 */
    Bmp_xppm = Bmp_yppm = 0;
    Bmp_image_size = tp->height*Real_width;
    Bmp_size = Bmp_image_size + HEADERSIZE;
    Bmp_headbuf[0] = 'B'; Bmp_headbuf[1] = 'M';
    memcpy(Bmp_headbuf + 2, &Bmp_size, sizeof(Bmp_size));
    Bmp_headbuf[6] = Bmp_headbuf[7] = Bmp_headbuf[8] = Bmp_headbuf[9] = 0;
    memcpy(Bmp_headbuf + 10, &Bmp_header_size, sizeof(Bmp_header_size));
    Bmp_headbuf[11] = Bmp_headbuf[12] = Bmp_headbuf[13] = 0;
    memcpy(Bmp_headbuf + 14, &Bmp_info_header_size, sizeof(Bmp_info_header_size));
    Bmp_headbuf[15] = Bmp_headbuf[16] = Bmp_headbuf[17] = 0;
    memcpy(Bmp_headbuf + 18, &tp->width, sizeof(Bmp_width));
    memcpy(Bmp_headbuf + 22, &tp->height, sizeof(Bmp_height));
    memcpy(Bmp_headbuf + 26, &Bmp_planes, sizeof(Bmp_planes));
    memcpy(Bmp_headbuf + 28, &Bmp_color, sizeof(Bmp_color));
    Bmp_headbuf[30] = Bmp_headbuf[31] = Bmp_headbuf[32] = Bmp_headbuf[33] = 0;
    memcpy(Bmp_headbuf + 34, &Bmp_image_size, sizeof(Bmp_image_size));
    memcpy(Bmp_headbuf + 38, &Bmp_xppm, sizeof(Bmp_xppm));
    memcpy(Bmp_headbuf + 42, &Bmp_yppm, sizeof(Bmp_yppm));
    Bmp_headbuf[46] = Bmp_headbuf[47] = Bmp_headbuf[48] = Bmp_headbuf[49] = 0;
    Bmp_headbuf[50] = Bmp_headbuf[51] = Bmp_headbuf[52] = Bmp_headbuf[53] = 0;

    /* ヘッダ情報書き出し */
    fwrite(Bmp_headbuf, sizeof(unsigned char), HEADERSIZE, Out_Fp);

    /* 画像データ書き出し */
    for (i = 0; i < tp->height; i++) {
        for (j = 0; j < tp->width; j++) {
            Bmp_Data[j * 3    ] = tp->data[tp->height - i - 1][j].b;
            Bmp_Data[j * 3 + 1] = tp->data[tp->height - i - 1][j].g;
            Bmp_Data[j * 3 + 2] = tp->data[tp->height - i - 1][j].r;
        }
        for (j = tp->width * 3; j < Real_width; j++) {
            Bmp_Data[j] = 0;
        }
        fwrite(Bmp_Data, sizeof(unsigned char), Real_width, Out_Fp);
    }

    /* 動的に確保した配列領域の解放 */
    free(Bmp_Data);

    /* ファイルクローズ */
    fclose(Out_Fp);
}


void drawGrid(color lineclr1, color lineclr2, color lineclr3)
{
    int i, j, k;
    int img_width = bmp_img->width;
    int img_height = bmp_img->height;

    for (i = 0; i < _panel_cols + 1; i++) {
        for (j = 0; j < img_width; j++) {
            for (k = 0; k < LINE_WIDTH; k++) {
                bmp_img->data[i*(PIXEL_WIDTH + LINE_WIDTH) + SCALE_LENGTH + k][j] = lineclr1;
            }
        }
    }
    for (i = 0; i < _panel_rows + 1; i++) {
        for (j = 0; j < img_height; j++) {
            for (k = 0; k < LINE_WIDTH; k++) {
                bmp_img->data[j][i*(PIXEL_WIDTH + LINE_WIDTH) + SCALE_LENGTH + k] = lineclr1;
            }
        }
        if (i % 5 == 0 && i > 0) {
            for (j = 0; j < SCALE_LENGTH; j++) {
                bmp_img->data[j][i*(PIXEL_WIDTH + LINE_WIDTH) + SCALE_LENGTH - 1] = lineclr2;
                bmp_img->data[j][i*(PIXEL_WIDTH + LINE_WIDTH) + SCALE_LENGTH + LINE_WIDTH] = lineclr2;
            }
            for (j = bmp_img->width - SCALE_LENGTH; j < bmp_img->width; j++) {
                bmp_img->data[j][i*(PIXEL_WIDTH + LINE_WIDTH) + SCALE_LENGTH - 1] = lineclr2;
                bmp_img->data[j][i*(PIXEL_WIDTH + LINE_WIDTH) + SCALE_LENGTH + LINE_WIDTH] = lineclr2;
            }
            for (j = 0; j < img_height; j++) {
                for (k = 0; k < LINE_WIDTH; k++) {
                    bmp_img->data[j][i*(PIXEL_WIDTH + LINE_WIDTH) + SCALE_LENGTH + k] = lineclr2;
                }
            }
        }
        if (i % 10 == 0 && i > 0) {
            for (j = 0; j < SCALE_LENGTH; j++) {
                for (k = 1; k < 3; k++) {
                    bmp_img->data[j][i*(PIXEL_WIDTH + LINE_WIDTH) + SCALE_LENGTH - k] = lineclr3;
                    bmp_img->data[j][i*(PIXEL_WIDTH + LINE_WIDTH) + SCALE_LENGTH + LINE_WIDTH + k - 1] = lineclr3;
                }
            }
            for (j = bmp_img->width - SCALE_LENGTH; j < bmp_img->width; j++) {
                for (k = 1; k < 3; k++) {
                    bmp_img->data[j][i*(PIXEL_WIDTH + LINE_WIDTH) + SCALE_LENGTH - k] = lineclr3;
                    bmp_img->data[j][i*(PIXEL_WIDTH + LINE_WIDTH) + SCALE_LENGTH + LINE_WIDTH + k - 1] = lineclr3;
                }
            }
            for (j = 0; j < img_height; j++) {
                for (k = 0; k < LINE_WIDTH; k++) {
                    bmp_img->data[j][i*(PIXEL_WIDTH + LINE_WIDTH) + SCALE_LENGTH + k] = lineclr3;
                }
            }
        }
    }
    for (i = 0; i < _panel_cols + 1; i++) {
        if (i % 5 == 0 && i > 0) {
            for (j = 0; j < SCALE_LENGTH; j++) {
                bmp_img->data[i*(PIXEL_WIDTH + LINE_WIDTH) + SCALE_LENGTH - 1][j] = lineclr2;
                bmp_img->data[i*(PIXEL_WIDTH + LINE_WIDTH) + SCALE_LENGTH + LINE_WIDTH][j] = lineclr2;
            }
            for (j = bmp_img->width - SCALE_LENGTH; j < bmp_img->width; j++) {
                bmp_img->data[i*(PIXEL_WIDTH + LINE_WIDTH) + SCALE_LENGTH - 1][j] = lineclr2;
                bmp_img->data[i*(PIXEL_WIDTH + LINE_WIDTH) + SCALE_LENGTH + LINE_WIDTH][j] = lineclr2;
            }
            for (j = 0; j < img_width; j++) {
                for (k = 0; k < LINE_WIDTH; k++) {
                    bmp_img->data[i*(PIXEL_WIDTH + LINE_WIDTH) + SCALE_LENGTH + k][j] = lineclr2;
                }
            }
        }
        if (i % 10 == 0 && i > 0) {
            for (j = 0; j < SCALE_LENGTH; j++) {
                for (k = 1; k < 3; k++) {
                    bmp_img->data[i*(PIXEL_WIDTH + LINE_WIDTH) + SCALE_LENGTH - k][j] = lineclr3;
                    bmp_img->data[i*(PIXEL_WIDTH + LINE_WIDTH) + SCALE_LENGTH + LINE_WIDTH + k - 1][j] = lineclr3;
                }
            }
            for (j = bmp_img->width - SCALE_LENGTH; j < bmp_img->width; j++) {
                for (k = 1; k < 3; k++) {
                    bmp_img->data[i*(PIXEL_WIDTH + LINE_WIDTH) + SCALE_LENGTH - k][j] = lineclr3;
                    bmp_img->data[i*(PIXEL_WIDTH + LINE_WIDTH) + SCALE_LENGTH + LINE_WIDTH + k - 1][j] = lineclr3;
                }
            }
            for (j = 0; j < img_width; j++) {
                for (k = 0; k < LINE_WIDTH; k++) {
                    bmp_img->data[i*(PIXEL_WIDTH + LINE_WIDTH) + SCALE_LENGTH + k][j] = lineclr3;
                }
            }
        }
    }
}


void setPanelSize(int rows, int cols)
{
    if(rows <= 0) _panel_rows = 64;
    else          _panel_rows = rows;

    if(cols <= 0) _panel_cols = 64;
    else          _panel_cols = cols;
}


void initBmpImg()
{
    int i;

    img_canvas = (color**)malloc(sizeof(color*) * _panel_rows);
    for(i = 0; i < _panel_rows; i++)
        img_canvas[i] = (color*)calloc(_panel_cols, sizeof(color));

    bmp_img = (img*)malloc(sizeof(img));
    bmp_img->width = (LINE_WIDTH + PIXEL_WIDTH) * _panel_cols + LINE_WIDTH + SCALE_LENGTH * 2;
    bmp_img->height = (LINE_WIDTH + PIXEL_WIDTH) * _panel_rows + LINE_WIDTH + SCALE_LENGTH * 2;
    bmp_img->data = (color**)malloc(sizeof(color*) * bmp_img->height);
    for(i = 0; i < bmp_img->height; i++)
        bmp_img->data[i] = (color*)calloc(bmp_img->width, sizeof(color));
}

void takeTimelapse()
{
    if(disable_recording) return;
    int i;
    //"log/rectmp/0000.bmp"
    char fname[21];

    mkdir("log", 0766);
    mkdir("log/rectmp", 0766);

    for(i = 1; i < 10000; i++) {
        sprintf(fname, "log/rectmp/%04d.bmp", i);
        WriteBmp(fname, bmp_img);
        usleep(1000000 / recording_fps);
    }
    fprintf(stdout, "Reached maximum recording time\n");
}

void initBmpImage( img *img_ptr, int width, int height)
{
    int i;

    img_ptr->data = (color**)malloc(sizeof(color*) * height);
    for(i = 0; i <height; i++)
        img_ptr->data[i] = (color*)calloc( width, sizeof(color));
    img_ptr->width = width;
    img_ptr->height = height;
}

void freeBmpImage( img *img_ptr)
{
    int i;

    if( img_ptr==NULL || img_ptr->data==NULL) return;
    for(i = 0; i <img_ptr->height; i++){
        free( img_ptr->data[i]);
    }
    free( img_ptr->data);
    img_ptr->width = 0;
    img_ptr->height = 0;
}
