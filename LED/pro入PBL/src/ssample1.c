led_matrix_swap_on_vsync(matrix, offscreen_canvas);#include <stdio.h>
#include <unistd.h>
#include <pthread.h>
#include <string.h>
#include "led-matrix-c.h"
#include "mnb_bmp.h"

int main(int argc, char const **argv)
{
    struct RGBLedMatrixOptions options;
    struct RGBLedMatrix *matrix;
    struct LedCanvas *offscreen_canvas;
    char rgb_sequence[] = "GBR";

    memset(&options, 0, sizeof(options));
    options.rows = options.cols = 64;
    options.led_rgb_sequence = rgb_sequence;
    matrix = led_matrix_create_from_options(&options, &argc, (char***)&argv);
    if (matrix == NULL) return 1;
    offscreen_canvas = led_matrix_create_offscreen_canvas(matrix);

    pthread_t recthread;
    if(pthread_create(&recthread, NULL, (void*)takeTimelapse, NULL)) {
        return -1;
    }

    int width, height;
    led_canvas_get_size(offscreen_canvas, &width, &height);





//みなさんが書き換えるのはこれ以降の部分
//あらかじめ宣言されいて使用可能な変数は，以下の4つ
//  int width, heigh; //width=64, height=64です
//  struct RGBLedMatrix *matrix; //LEDディスプレイパネルを表す変数
//  struct LedCanvas *offscreen_canvas; //バッファ
//LEDディスプレイパネルを光らせるのに使用する特別な関数は以下の4つのみ
//  void led_canvas_clear(struct LedCanvas *canvas); //LEDディスプレイパネル前面を黒にする
//  void led_canvas_set_pixel(struct LedCanvas *canvas, int x, int y,
//                            uint8_t r, uint8_t g, uint8_t b); //canvasのx,yにr,g,bの色を出す
//  struct LedCanvas *led_matrix_swap_on_vsync(struct RGBLedMatrix *matrix,
//                                             struct LedCanvas *canvas); //canvasの内容をLEDパネルに転送
//  int usleep(useconds_t usec); //usecマイクロ秒待機する．usecは1000000（1秒）まで
//静止画1枚目を作る
    led_canvas_clear(offscreen_canvas); //canvasをクリア

    int i, j;

    for( i=0; i<8; i++){
        for( j = 0; j <8; j++)
        {
         led_canvas_set_pixel(offscreen_canvas, i, j, 1, 255, 1);
        }
    }
    for( i=0; i<8; i++){
        for( j = 8; j <16; j++)
        {
         led_canvas_set_pixel(offscreen_canvas, i, j, 1, 1, 255);
        }
    }
    for( i=0; i<8; i++){
        for( j = 16; j <24; j++)
        {
         led_canvas_set_pixel(offscreen_canvas, i, j, 1, 244, 1);
        }
    }
    for( i=0; i<8; i++){
        for( j = 24; j <32; j++)
        {
         led_canvas_set_pixel(offscreen_canvas, i, j, 44, 1, 1);
        }
    }
    for( i=0; i<8; i++){
        for( j = 32; j <40; j++)
        {
         led_canvas_set_pixel(offscreen_canvas, i, j, 65, 61, 61);
        }
    }
    for( i=0; i<8; i++){
        for( j = 40; j <48; j++)
        {
         led_canvas_set_pixel(offscreen_canvas, i, j, 1, 55, 1);
        }
    }
    for( i=0; i<8; i++){
        for( j = 48; j <56; j++)
        {
         led_canvas_set_pixel(offscreen_canvas, i, j, 255, 1, 6);
        }
    }
    for( i=0; i<8; i++){
        for( j = 56; j <64; j++)
        {
         led_canvas_set_pixel(offscreen_canvas, i, j, 1, 1, 0);
        }
    }
    for( i=8; i<16; i++){
        for( j = 0; j <8; j++)
        {
         led_canvas_set_pixel(offscreen_canvas, i, j, 0, 0, 0);
        }
    }
    for( i=8; i<16; i++){
        for( j = 8; j <16; j++)
        {
         led_canvas_set_pixel(offscreen_canvas, i, j, 255, 255, 255);
        }
    }
    for( i=8; i<16; i++){
        for( j = 16; j <24; j++)
        {
         led_canvas_set_pixel(offscreen_canvas, i, j, 44, 44, 33);
        }
    }
    for( i=8; i<16; i++){
        for( j = 24; j <32; j++)
        {
         led_canvas_set_pixel(offscreen_canvas, i, j, 2, 66, 9);
        }
    }
    for( i=8; i<16; i++){
        for( j = 32; j <40; j++)
        {
         led_canvas_set_pixel(offscreen_canvas, i, j, 92, 226, 3);
        }
    }
    for( i=8; i<16; i++){
        for( j = 40; j <48; j++)
        {
         led_canvas_set_pixel(offscreen_canvas, i, j, 33, 23, 67);
        }
    }
    for( i=8; i<16; i++){
        for( j = 48; j <56; j++)
        {
         led_canvas_set_pixel(offscreen_canvas, i, j, 255, 2, 2);
        }
    }
    for( i=8; i<16; i++){
        for( j = 56; j <64; j++)
        {
         led_canvas_set_pixel(offscreen_canvas, i, j, 55, 2, 66);
        }
    }
    
    for( i=16; i<24; i++){
        for( j = 0; j <8; j++)
        {
         led_canvas_set_pixel(offscreen_canvas, i, j, 3, 224, 5);
        }
    }
    for( i=16; i<24; i++){
        for( j = 8; j <16; j++)
        {
         led_canvas_set_pixel(offscreen_canvas, i, j, 33, 43, 53);
        }
    }
    for( i=16; i<24; i++){
        for( j = 16; j <24; j++)
        {
         led_canvas_set_pixel(offscreen_canvas, i, j, 30, 43, 2);
        }
    }
    for( i=16; i<24; i++){
        for( j = 24; j <32; j++)
        {
         led_canvas_set_pixel(offscreen_canvas, i, j, 113, 114, 115);
        }
    }
    for( i=16; i<24; i++){
        for( j = 32; j <40; j++)
        {
         led_canvas_set_pixel(offscreen_canvas, i, j, 233, 224, 225);
        }
    }
    for( i=16; i<24; i++){
        for( j = 40; j <48; j++)
        {
         led_canvas_set_pixel(offscreen_canvas, i, j, 38, 40, 52);
        }
    }
    for( i=16; i<24; i++){
        for( j = 48; j <56; j++)
        {
         led_canvas_set_pixel(offscreen_canvas, i, j, 30, 40, 50);
        }
    }
    for( i=16; i<24; i++){
        for( j = 56; j <64; j++)
        {
         led_canvas_set_pixel(offscreen_canvas, i, j, 188, 88, 59);
        }
    }
    for( i=24; i<32; i++){
        for( j = 0; j <8; j++)
        {
         led_canvas_set_pixel(offscreen_canvas, i, j, 44, 44, 45);
        }
    }
    for( i=24; i<32; i++){
        for( j = 8; j <16; j++)
        {
         led_canvas_set_pixel(offscreen_canvas, i, j, 255, 114, 44);
        }
    }
    for( i=24; i<32; i++){
        for( j = 16; j <24; j++)
        {
         led_canvas_set_pixel(offscreen_canvas, i, j, 224, 114, 225);
        }
    }
    for( i=24; i<32; i++){
        for( j = 24; j <32; j++)
        {
         led_canvas_set_pixel(offscreen_canvas, i, j, 24, 14, 25);
        }
    }
    for( i=24; i<32; i++){
        for( j = 32; j <40; j++)
        {
         led_canvas_set_pixel(offscreen_canvas, i, j, 2, 1, 5);
        }
    }
    for( i=24; i<32; i++){
        for( j = 40; j <48; j++)
        {
         led_canvas_set_pixel(offscreen_canvas, i, j, 22, 14, 5);
        }
    }
    for( i=24; i<32; i++){
        for( j = 48; j <56; j++)
        {
         led_canvas_set_pixel(offscreen_canvas, i, j, 1, 1, 8);
        }
    }
    for( i=24; i<32; i++){
        for( j = 56; j <64; j++)
        {
         led_canvas_set_pixel(offscreen_canvas, i, j, 0, 0, 0);
        }
    }
    for( i=32; i<40; i++){
        for( j = 0; j <8; j++)
        {
         led_canvas_set_pixel(offscreen_canvas, i, j, 255, 255, 255);
        }
    }
    for( i=32; i<40; i++){
        for( j = 8; j <16; j++)
        {
         led_canvas_set_pixel(offscreen_canvas, i, j, 222, 24, 225);
        }
    }
    for( i=32; i<40; i++){
        for( j = 16; j <24; j++)
        {
         led_canvas_set_pixel(offscreen_canvas, i, j, 221, 41, 51);
        }
    }
    for( i=32; i<40; i++){
        for( j = 24; j <32; j++)
        {
         led_canvas_set_pixel(offscreen_canvas, i, j, 122, 14, 15);
        }
    }
    for( i=32; i<40; i++){
        for( j = 32; j <40; j++)
        {
         led_canvas_set_pixel(offscreen_canvas, i, j, 122, 224, 225);
        }
    }
    for( i=32; i<40; i++){
        for( j = 40; j <48; j++)
        {
         led_canvas_set_pixel(offscreen_canvas, i, j, 211, 4, 54);
        }
    }
    for( i=32; i<40; i++){
        for( j = 48; j <56; j++)
        {
         led_canvas_set_pixel(offscreen_canvas, i, j, 222, 34, 5);
        }
    }
    for( i=32; i<40; i++){
        for( j = 56; j <64; j++)
        {
         led_canvas_set_pixel(offscreen_canvas, i, j, 22, 41, 5);
        }
    }
    for( i=40; i<48; i++){
        for( j = 0; j <8; j++)
        {
         led_canvas_set_pixel(offscreen_canvas, i, j, 200, 45, 55);
        }
    }
    for( i=40; i<48; i++){
        for( j = 8; j <16; j++)
        {
         led_canvas_set_pixel(offscreen_canvas, i, j, 3, 44, 55);
        }
    }
    for( i=40; i<48; i++){
        for( j = 16; j <24; j++)
        {
         led_canvas_set_pixel(offscreen_canvas, i, j, 223, 43, 53);
        }
    }
    for( i=40; i<48; i++){
        for( j = 24; j <32; j++)
        {
         led_canvas_set_pixel(offscreen_canvas, i, j, 22, 4, 66);
        }
    }
    for( i=40; i<48; i++){
        for( j = 32; j <40; j++)
        {
         led_canvas_set_pixel(offscreen_canvas, i, j, 22, 4, 65);
        }
    }
    for( i=40; i<48; i++){
        for( j = 40; j <48; j++)
        {
         led_canvas_set_pixel(offscreen_canvas, i, j, 22, 46, 5);
        }
    }
    for( i=40; i<48; i++){
        for( j = 48; j <56; j++)
        {
         led_canvas_set_pixel(offscreen_canvas, i, j, 2, 4, 5);
        }
    }
    for( i=40; i<48; i++){
        for( j = 56; j <64; j++)
        {
         led_canvas_set_pixel(offscreen_canvas, i, j, 2, 45, 55);
        }
    }
    for( i=48; i<56; i++){
        for( j = 0; j <8; j++)
        {
         led_canvas_set_pixel(offscreen_canvas, i, j, 9, 0, 0);
        }
    }
    for( i=48; i<56; i++){
        for( j = 8; j <16; j++)
        {
         led_canvas_set_pixel(offscreen_canvas, i, j, 9, 228, 47);
        }
    }
    for( i=48; i<56; i++){
        for( j = 16; j <24; j++)
        {
         led_canvas_set_pixel(offscreen_canvas, i, j, 93, 85, 227);
        }
    }
    for( i=48; i<56; i++){
        for( j = 24; j <32; j++)
        {
         led_canvas_set_pixel(offscreen_canvas, i, j, 90, 18, 173);
        }
    }
    for( i=48; i<56; i++){
        for( j = 32; j <40; j++)
        {
         led_canvas_set_pixel(offscreen_canvas, i, j, 119, 28, 7);
        }
    }
    for( i=48; i<56; i++){
        for( j = 40; j <48; j++)
        {
         led_canvas_set_pixel(offscreen_canvas, i, j, 39, 38, 7);
        }
    }
    for( i=48; i<56; i++){
        for( j = 48; j <56; j++)
        {
         led_canvas_set_pixel(offscreen_canvas, i, j, 9, 83, 37);
        
    }
    }
    for( i=48; i<56; i++){
        for( j = 56; j <64; j++)
        {
         led_canvas_set_pixel(offscreen_canvas, i, j, 9, 8, 7);
        }
    }
    for( i=56; i<64; i++){
        for( j = 0; j <8; j++)
        {
         led_canvas_set_pixel(offscreen_canvas, i, j, 1, 2, 2);
        }
    }
    for( i=56; i<64; i++){
        for( j = 8; j <16; j++)
        {
         led_canvas_set_pixel(offscreen_canvas, i, j, 1, 222, 2);
        }
    }
    for( i=56; i<64; i++){
        for( j = 16; j <24; j++)
        {
         led_canvas_set_pixel(offscreen_canvas, i, j, 1, 2, 222);
        }
    }
    for( i=56; i<64; i++){
        for( j = 24; j <32; j++)
        {
         led_canvas_set_pixel(offscreen_canvas, i, j, 122, 2, 2);
        }
    }
    for( i=56; i<64; i++){
        for( j = 32; j <40; j++)
        {
         led_canvas_set_pixel(offscreen_canvas, i, j, 124, 42, 24);
        }
    }
    for( i=56; i<64; i++){
        for( j = 40; j <48; j++)
        {
         led_canvas_set_pixel(offscreen_canvas, i, j, 21, 211, 42);
        }
    }
    for( i=56; i<64; i++){
        for( j = 48; j <56; j++)
        {
         led_canvas_set_pixel(offscreen_canvas, i, j, 155, 42, 82);
        }
    }
    for( i=56; i<64; i++){
        for( j = 56; j <64; j++)
        {
         led_canvas_set_pixel(offscreen_canvas, i, j, 10, 2, 20);
        }
    }
    
    led_matrix_swap_on_vsync(matrix, offscreen_canvas); //canvasの内容をLEDパネルに転送
//ここで2枚目ができる


//みなさんが書き換えるのはここまで




    return 0;
}
