#include <stdio.h>
#include <unistd.h>         //ドラえもん
#include <pthread.h>
#include <string.h>
#include "led-matrix-c.h"
#include "mnb_bmp.h"
#include <math.h>

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

    double i, j;
    double m;
    int t, k;
        led_canvas_clear(offscreen_canvas); //canvasをクリア
        //顔
    for( i=0; i<5000; ++i){

        led_canvas_set_pixel(offscreen_canvas, 32*cos(2*M_PI*(i/5000))+32, 32*sin(2*M_PI*(i/5000))+32, 0, 0, 255);
        led_canvas_set_pixel(offscreen_canvas, 30*cos(2*M_PI*(i/5000))+32, 25*sin(2*M_PI*(i/5000))+38, 0, 0, 255);

        led_matrix_swap_on_vsync(matrix, offscreen_canvas); //canvasの内容をLEDパネルに転送
        usleep(50); 
    }

    //、目
    for( i=0; i<5000; ++i){

        led_canvas_set_pixel(offscreen_canvas, 5*cos(2*M_PI*i/5000)+27, 8*sin(2*M_PI*i/5000)+16, 255, 255, 255);
        led_canvas_set_pixel(offscreen_canvas, 5*cos(2*M_PI*i/5000)+37, 8*sin(2*M_PI*i/5000)+16, 255, 255, 255);

        led_matrix_swap_on_vsync(matrix, offscreen_canvas); //canvasの内容をLEDパネルに転送
        usleep(50); 
    }

    for( i=27; i<30; i++){
        for( j =19; j <22; j++)
        {
         led_canvas_set_pixel(offscreen_canvas, i, j, 255, 255, 0);
        }
    }
    for( i=34; i<37; i++){
        for( j = 19; j <22; j++)
        {
         led_canvas_set_pixel(offscreen_canvas, i, j, 255, 255, 0);
        }
    }
     //鼻
   for( i=0; i<5000; ++i){

        led_canvas_set_pixel(offscreen_canvas, 4*cos(2*M_PI*i/5000)+32, 4*sin(2*M_PI*i/5000)+28, 255, 0, 0);

        led_matrix_swap_on_vsync(matrix, offscreen_canvas); //canvasの内容をLEDパネルに転送
        usleep(50); 
   }

    for( m = 32; m <38; m++) {

        led_canvas_set_pixel(offscreen_canvas, 32, m, 255, 255, 255);

        led_matrix_swap_on_vsync(matrix, offscreen_canvas); //canvasの内容をLEDパネルに転送
        usleep(10000); 
    }
    
    //口
    //上部分

    for( m=16; m<48; ++m){
        
        led_canvas_set_pixel(offscreen_canvas, m, 37, 255, 255, 255);

        led_matrix_swap_on_vsync(matrix, offscreen_canvas); //canvasの内容をLEDパネルに転送
        usleep(10000); 

    }

    //下部分
    for(m=16;m<32;++m){

       led_canvas_set_pixel(offscreen_canvas, m, m+22,255, 255, 255);

        
        led_matrix_swap_on_vsync(matrix, offscreen_canvas); //canvasの内容をLEDパネルに転送
        usleep(10000); 
    }
    for(m=32;m<48;++m){

        led_canvas_set_pixel(offscreen_canvas, m, -1*m+84,255, 255, 255);
        
        led_matrix_swap_on_vsync(matrix, offscreen_canvas); //canvasの内容をLEDパネルに転送
        usleep(10000); 
    }
    //ひげ
     for(m=10;m<22;++m){

        led_canvas_set_pixel(offscreen_canvas, m, m+2,255, 255, 255);

        
        led_matrix_swap_on_vsync(matrix, offscreen_canvas); //canvasの内容をLEDパネルに転送
        usleep(10000); 
    } for(m=5;m<22;++m){

        led_canvas_set_pixel(offscreen_canvas, m, 28,255, 255, 255);

        
        led_matrix_swap_on_vsync(matrix, offscreen_canvas); //canvasの内容をLEDパネルに転送
        usleep(10000); 
    } for(m=10;m<22;++m){

        led_canvas_set_pixel(offscreen_canvas, m, -1*m+53,255, 255, 255);

        
        led_matrix_swap_on_vsync(matrix, offscreen_canvas); //canvasの内容をLEDパネルに転送
        usleep(10000); 
    }
    //ひげ2
     for(m=42;m<54;++m){

        led_canvas_set_pixel(offscreen_canvas, m, m-10,255, 255, 255);

        
        led_matrix_swap_on_vsync(matrix, offscreen_canvas); //canvasの内容をLEDパネルに転送
        usleep(10000); 
    } for(m=43;m<60;++m){

        led_canvas_set_pixel(offscreen_canvas, m, 28,255, 255, 255);

        
        led_matrix_swap_on_vsync(matrix, offscreen_canvas); //canvasの内容をLEDパネルに転送
        usleep(10000); 
    }
     for(m=42;m<54;++m){

        led_canvas_set_pixel(offscreen_canvas, m, -1*m+65,255, 255, 255);

        
        led_matrix_swap_on_vsync(matrix, offscreen_canvas); //canvasの内容をLEDパネルに転送
        usleep(10000); 
     }
        usleep(3000000); 
//2
        
    for( t=0; t<500; ++t){
        for(k=0;k<500; ++k){
          led_canvas_set_pixel(offscreen_canvas, t-k, 31.5*sin((t*k)/500)+32, 32*(t/8), 200, 255-4*k); //(i,i)に赤い点を打つ
        }
        led_matrix_swap_on_vsync(matrix, offscreen_canvas); //canvasの内容をLEDパネルに転送
        usleep(9000); //100ミリ秒待機
    }

    //E
    for(m=5;m<19;++m){

        led_canvas_set_pixel(offscreen_canvas, m, 10, 255, 255, 0);
        led_canvas_set_pixel(offscreen_canvas, m, 17, 255, 255, 0);
        led_matrix_swap_on_vsync(matrix, offscreen_canvas); //canvasの内容をLEDパネルに転送
        led_canvas_set_pixel(offscreen_canvas, m, 24, 255, 255, 0);

        led_matrix_swap_on_vsync(matrix, offscreen_canvas); //canvasの内容をLEDパネルに転送
        usleep(10000); 
    }
    for(m=10;m<25;++m){

        led_canvas_set_pixel(offscreen_canvas, 5, m, 255, 255, 0);

        
        led_matrix_swap_on_vsync(matrix, offscreen_canvas); //canvasの内容をLEDパネルに転送
        usleep(10000); 
    }
    //N
    for(m=25;m<39;++m){

        led_canvas_set_pixel(offscreen_canvas, 23, m, 255, 0, 255);
        led_canvas_set_pixel(offscreen_canvas, m-1, m, 255, 0, 255);
        led_canvas_set_pixel(offscreen_canvas, 37, m, 255, 0, 255);

        
        led_matrix_swap_on_vsync(matrix, offscreen_canvas); //canvasの内容をLEDパネルに転送
        usleep(10000); 
    }
    //D
     for(m=41;m<60;++m){

        led_canvas_set_pixel(offscreen_canvas, 42, m, 0, 255, 255);

        
        led_matrix_swap_on_vsync(matrix, offscreen_canvas); //canvasの内容をLEDパネルに転送
        usleep(10000); 
    }

     for(m=41;m<52;++m){

        led_canvas_set_pixel(offscreen_canvas, m+1, (0.5)*m+21, 0, 255, 255);

        
        led_matrix_swap_on_vsync(matrix, offscreen_canvas); //canvasの内容をLEDパネルに転送
        usleep(10000); 
     }
     for(m=41;m<52;++m){

        led_canvas_set_pixel(offscreen_canvas, m+1, -(0.5)*m+80, 0, 255, 255);

        
        led_matrix_swap_on_vsync(matrix, offscreen_canvas); //canvasの内容をLEDパネルに転送
        usleep(10000); 
     }
     for(m=46;m<55;++m){

        led_canvas_set_pixel(offscreen_canvas, 52, m, 0, 255, 255);

        
        led_matrix_swap_on_vsync(matrix, offscreen_canvas); //canvasの内容をLEDパネルに転送
        usleep(10000); 
    }
     usleep(3000000); 

        
    return 0;
}
