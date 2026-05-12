#include <stdio.h>
#include <stdlib.h>
#include <time.h>

int main(void )
{
   char  c[128];
   int   a,b;

   system("cls");
   printf("hyyy");                   

   while ( 1 )
     {
       printf("\nD‚«‚È”Žš‚ð‚Ç‚¤‚¼: ");
     a=atoi(c);
       if ( a==0 ) break;

       b=rand( )%10+1;                      // —””­¶

       printf(" >>> ");

       switch ( (a+b)%10 )
         {
           case  0: printf("‘å‹g"); break;
           case  1: printf("‹g"); break;
           case  2: printf("‹g"); break;
           case  3: printf("‹g"); break;
           case  4: printf("‹g"); break;
           case  5: printf("‹g"); break;
           case  6: printf("‹¥"); break;
           case  7: printf("‹¥"); break;
           case  8: printf("‹¥"); break;
           case  9: printf("‘å‹¥"); break;
         }
       printf("\n");
    }
}
