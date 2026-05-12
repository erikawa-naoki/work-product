#include "led-matrix-c.h"
#include "mnb_bmp.h"
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <sys/stat.h>
#include <time.h>

struct RGBLedMatrix {};

struct RGBLedMatrix *led_matrix_create_from_options(
        struct RGBLedMatrixOptions *options,
        int *argc,
        char ***argv)
{
    int i, x;
    char s[4];

    for(i = 1; i < *argc; i++) {
        if(!strncmp((*argv)[i], "--led-rows=", strlen("--led-rows="))) {
            //--led-rows
            strncpy(s, (*argv)[i]+11, strlen((*argv)[i])-11);
            x = atoi(s);
            if(x <= 0 | x >= 1000) {
                s[strlen(s)] = '\0';
                fprintf(stderr, "set 64 size as %s is invalid value\n", s);
            } else {
                options->rows = atoi(s);
            }
        } else if(!strncmp((*argv)[i], "--led-cols=", strlen("--led-cols="))) {
            //--led-cols
            strncpy(s, (*argv)[i]+11, strlen((*argv)[i])-11);
            x = atoi(s);
            if(x <= 0 | x >= 1000) {
                s[strlen(s)] = '\0';
                fprintf(stderr, "set 64 size as %s is invalid value\n", s);
            } else {
                options->cols = atoi(s);
            }
        } else if(!strcmp((*argv)[i], "--disable-recording")) {
            //--disable_recording
            disable_recording = 1;
            char now[14];
            size_t t = time(NULL);
            strftime(now, sizeof(now), "%m%d_%H-%M-%S", localtime(&t));
            strcat(log_image_path, "log/led_matrix_");
            strcat(log_image_path, now);
            strcat(log_image_path, "/");

            // log/ にディレクトリを作成する場合は先に log/ が必要
            mkdir("log", 0766);
            mkdir(log_image_path, 0766);
        } else if(!strncmp((*argv)[i], "--fps=", strlen("--fps="))) {
            //--fps
            strncpy(s, (*argv)[i] + strlen("--fps="), strlen((*argv)[i]) - strlen("--fps="));
            x = atoi(s);
            if(x <= 0 || 30 < x) {
                s[strlen(s)] = '\0';
                fprintf(stderr, "set 30 fps as %s is invalid value", s);
            } else {
                recording_fps = x;
            }
        }
    }
    setPanelSize(options->rows, options->cols);
    initBmpImg();
    struct RGBLedMatrix *matrix = (struct RGBLedMatrix*)malloc(sizeof(struct RGBLedMatrix));
    return matrix;
}


struct RGBLedMatrix *led_matrix_create_from_options_const_argv(
        struct RGBLedMatrixOptions *options,
        int argc,
        char ***argv)
{
    return led_matrix_create_from_options(options, &argc, argv);
}


struct RGBLedMatrix *led_matrix_create(int rows, int chained, int parallel)
{
    setPanelSize(rows, 64);
    initBmpImg();
    struct RGBLedMatrix *matrix = (struct RGBLedMatrix*)malloc(sizeof(struct RGBLedMatrix));
    return matrix;
}


void led_matrix_delete(struct RGBLedMatrix *matrix)
{
    return;
}


struct LedCanvas *led_matrix_get_canvas(struct RGBLedMatrix *matrix)
{
    struct LedCanvas *c;
    return c;
}


void led_canvas_get_size(const struct LedCanvas *canvas, int *width, int *height)
{
    *width = _panel_cols;
    *height = _panel_rows;
}

void led_canvas_set_pixel(struct LedCanvas *c, int x, int y, uint8_t r, uint8_t g, uint8_t b)
{
    if (x < 0 || x >= _panel_cols || y < 0 || y >= _panel_rows) return;

    img_canvas[y][x].r = r;
    img_canvas[y][x].g = g;
    img_canvas[y][x].b = b;
}


void led_canvas_clear(struct LedCanvas *c)
{
    led_canvas_fill(c, 0, 0, 0);
}


void led_canvas_fill(struct LedCanvas *c, uint8_t r, uint8_t g, uint8_t b)
{
    int i, j;

    for (i = 0; i < _panel_rows; i++) {
        for (j = 0; j < _panel_cols; j++) {
            led_canvas_set_pixel(c, j, i, r, g, b);
        }
    }
}


struct LedCanvas *led_matrix_create_offscreen_canvas(struct RGBLedMatrix *matrix)
{
    struct LedCanvas *c;
    return c;
}


struct LedCanvas *led_matrix_swap_on_vsync(struct RGBLedMatrix *matrix, struct LedCanvas *canvas)
{
    int i, j, k, l, xx, yy;

    for(i = 0; i < _panel_rows; i++) {
        for(j = 0; j < _panel_cols; j++) {
            for (k = 0; k < PIXEL_WIDTH; k++) {
                for (l = 0; l < PIXEL_WIDTH; l++) {
                    //hard coding PIXEL_WIDTH is 5
                    if((!k && !l)||(!k && l==4)||(k==4 && !l)||(k==4 && l==4)) continue;

                    xx = k + (LINE_WIDTH + PIXEL_WIDTH) * j + LINE_WIDTH + SCALE_LENGTH;
                    yy = l + (LINE_WIDTH + PIXEL_WIDTH) * i + LINE_WIDTH + SCALE_LENGTH;
                    bmp_img->data[yy][xx].r = img_canvas[i][j].r;
                    bmp_img->data[yy][xx].g = img_canvas[i][j].g;
                    bmp_img->data[yy][xx].b = img_canvas[i][j].b;
                }
            }
        }
    }

    if(disable_recording) {
        char fname[64] = "";
        char img_fname[9];
        sprintf(img_fname, "%04d.bmp", still_image_count++);
        strcat(fname, log_image_path);
        strcat(fname, img_fname);
        WriteBmp(fname, bmp_img);
    }
    return canvas;
}
