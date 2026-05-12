#include <stdio.h>
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

    int i, j;

    led_canvas_clear(offscreen_canvas); //canvasをクリア
for( i=0; i<32; i++){
    for(j=0; j<32; j=j+2){

         led_canvas_set_pixel(offscreen_canvas, i+32, i, 255, 255, 255);
    }
    }
for( i=0; i<32; i++){
    for(j=0; j<32; j=j+2){

         led_canvas_set_pixel(offscreen_canvas, i+32, i+4, 255, 255, 255);
    }
    }
for( i=0; i<32; i++){
    for(j=0; j<32; j=j+2){

         led_canvas_set_pixel(offscreen_canvas, i+32, i+8, 255, 255, 255);
    }
    }
for( i=0; i<32; i++){
    for(j=0; j<32; j=j+2){

         led_canvas_set_pixel(offscreen_canvas, i+32, i+12, 255, 255, 255);
    }
    }
for( i=0; i<32; i++){
    for(j=0; j<32; j=j+2){

         led_canvas_set_pixel(offscreen_canvas, i+32, i+16, 255, 255, 255);
    }
    }
for( i=0; i<32; i++){
    for(j=0; j<32; j=j+2){

         led_canvas_set_pixel(offscreen_canvas, i+32, i+20, 255, 255, 255);
    }
    }
for( i=0; i<32; i++){
    for(j=0; j<32; j=j+2){

         led_canvas_set_pixel(offscreen_canvas, i+32, i+24, 255, 255, 255);
    }
    }
for( i=0; i<32; i++){
    for(j=0; j<32; j=j+2){

         led_canvas_set_pixel(offscreen_canvas, i+32, i+28, 255, 255, 255);
    }
    }
for( i=0; i<32; i++){
    for(j=0; j<32; j=j+2){

         led_canvas_set_pixel(offscreen_canvas, i+32, i+32, 255, 255, 255);
    }
    }
for( i=0; i<32; i++){
    for(j=0; j<32; j=j+2){

         led_canvas_set_pixel(offscreen_canvas, i+32, i-4, 255, 255, 255);
    }
    }
for( i=0; i<32; i++){
    for(j=0; j<32; j=j+2){

         led_canvas_set_pixel(offscreen_canvas, i+32, i-8, 255, 255, 255);
    }
    }
for( i=0; i<32; i++){
    for(j=0; j<32; j=j+2){

         led_canvas_set_pixel(offscreen_canvas, i+32, i-12, 255, 255, 255);
    }
    }
for( i=0; i<32; i++){
    for(j=0; j<32; j=j+2){

         led_canvas_set_pixel(offscreen_canvas, i+32, i-16, 255, 255, 255);
    }
    }
for( i=0; i<32; i++){
    for(j=0; j<32; j=j+2){

         led_canvas_set_pixel(offscreen_canvas, i+32, i-20, 255, 255, 255);
    }
    }
for( i=0; i<32; i++){
    for(j=0; j<32; j=j+2){

         led_canvas_set_pixel(offscreen_canvas, i+32, i-24, 255, 255, 255);
    }
    }
for( i=0; i<32; i++){
    for(j=0; j<32; j=j+2){

         led_canvas_set_pixel(offscreen_canvas, i+32, i-28, 255, 255, 255);
    }
    }
for( i=0; i<32; i++){
    for(j=0; j<32; j=j+2){

         led_canvas_set_pixel(offscreen_canvas, i+32, i-32, 255, 255, 255);
    }
    }
for( i=0; i<32; i++){
    for(j=0; j<32; j++){
         led_canvas_set_pixel(offscreen_canvas, i, j, 255, 0, 0);
      } 
    }
for( i=0; i<35; i=i+2){
    for(j=0; j<35; j=j+2){
         led_canvas_set_pixel(offscreen_canvas, i+32, j+32, 0, 0, 255);
      } 
    }
for( i=0; i<35; i=i+2){
    for(j=0; j<35; j=j+2){
         led_canvas_set_pixel(offscreen_canvas, i+33, j+33, 0, 0, 255);
      } 
    }
    for( i=0; i<32; i=i+4){
       for( j=0; j<32; j++){

        led_canvas_set_pixel(offscreen_canvas, i, j+32, 0, 255, 0);

       }
    }
        led_matrix_swap_on_vsync(matrix, offscreen_canvas);



    return 0;
}
