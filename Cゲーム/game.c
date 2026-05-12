#include <stdio.h>
#include <stdlib.h>

#include <unistd.h>
#include <fcntl.h>

#include <termios.h>
#include <string.h>

#define ROW 15 
#define COL 20
#define SLEEP 10000

#define clrscr() printf("\e[1;1H\e[2J")

struct termios orig_termios;

void reset_terminal_mode()
{
    tcsetattr(0, TCSANOW, &orig_termios);
}

void set_conio_terminal_mode()
{
    struct termios new_termios;

    /* take two copies - one for now, one for later */
    tcgetattr(0, &orig_termios);
    memcpy(&new_termios, &orig_termios, sizeof(new_termios));

    /* register cleanup handler, and set the new terminal mode */
    atexit(reset_terminal_mode);
    cfmakeraw(&new_termios);
    tcsetattr(0, TCSANOW, &new_termios);
}



initscreen(char game[ROW][COL])
     {int i, j;

       for(i=0; i<ROW; i++)
       { for(j=0; j<COL; j++)
         { game[i][j]=' ';
         }
         printf("\n");
       }
     }

showscreen(char game[ROW][COL])
{int i, j;

       printf(" --------------------\n");
       for(i=ROW-1; i>=0; i--)
       {
         printf("%c", 0x0D);
         printf("|");
	 for(j=0; j<COL; j++)
         {  printf("%c", game[i][j]);
         }
         printf("|\n");
       }
       printf("%c", 0x0D);
       printf(" --------------------\n");
}


int main(int argc, char *argv[]) 
{
  //struct termios t;

  char ch;
  char str[40];
  int n, t0, invaderROW, invaderCOL;
  char game[ROW][COL];
  int counter;
  int missileROW, missileCOL, missileFIRED;

    printf("a to left, or l to right\n");
    printf("x to quit\n");
    printf("Hit return to start\n");
    getchar();

//system("stty erase ^H);
//system("stty -F /dev/ttyS0 -icrnl -ixon -ixoff -opost -isig -icanon -echo");    // enter into non-canonical (raw) mode

  set_conio_terminal_mode();

    initscreen(game);
/*
 //   tcgetattr(0, &t);
//    t.c_lflag &= ~ICANON;
 //   tcsetattr(0, TCSANOW, &t);
 //   */

    fcntl(0, F_SETFL, fcntl(0, F_GETFL) | O_NONBLOCK);

    t0=9;
    game[0][t0] = '^';
    missileROW = 0;
 
    counter = 0;
    while (1) 
    {
      /* {int delay, d1;
	       for(d1=0; d1<999; d1++)
	       {
                  for(delay=0; delay<9999; delay++);
	       }
       }*/

      usleep(70000);
      clrscr();

      counter++;
      if( !(counter % 17) )
      {
        if( invaderROW == 0 )
        {   game[invaderROW][invaderCOL]=' ';
        }

        if( invaderROW > 0)
	{ game[invaderROW][invaderCOL]=' ';
          invaderROW--;
          game[invaderROW][invaderCOL]='*';
	}
        else
	{ invaderROW=ROW-1;
          invaderCOL= rand()%20;
          game[invaderROW][invaderCOL]='*';
	}
      }

      if( !(counter % 10) )
      {
        if( missileROW >= ROW-1 )
        {   game[missileROW][missileCOL]=' ';
            missileROW=0;
        }

        if( missileROW > 0)
	{ game[missileROW][missileCOL]=' ';
          missileROW++;
          game[missileROW][missileCOL]='^';
	}
        else
	{;
	}
      }

	ch = 'Z'; 
	read (0, &ch, 1);
	showscreen(game);

        if( ch == 'l' )
            {     if( 0<= t0 && t0<COL-1 )
                    { game[0][t0] = ' ';
                      if( t0<COL-1 )
                      { t0++;
                        game[0][t0] = '^';
                      }
                    }
            }

        else if( ch == 'a' )
            {       if( 0< t0 && t0<COL )
                    { game[0][t0] = ' ';
                      if( t0>0 )
                      { t0--;
                        game[0][t0] = '^';
                      }
                    }
            }
        else if( ch == ' ' )
            {      
		    missileCOL = t0;
		    missileROW = 1;
                    game[1][t0] = '^';
            }
        else if( ch == 'x' )
            {   break;
            }

    }

    return 0; 
}
