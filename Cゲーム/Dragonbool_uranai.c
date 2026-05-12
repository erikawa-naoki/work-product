#include <stdio.h>        //ドラゴンボール占い

int main(void)
{
  int a, b, x;

    printf("オッス！オラ悟空！\n元気なおめぇはもっと元気に!\n落ち込んでるおめぇももっと元気に!\nドラゴンボール占いはじまっぞ!\n");

      printf("\n０～１０のなかで好きな数2字を入力してくれ!:");
      scanf("%d", &a);
      printf("\nもっかい０～１０のなかで好きな数字を入力してくれよな!:");
      scanf("%d", &b);

      switch ((a + b) % 10){
        case 0:
            printf("      ____________      \n");
            printf("    ／            ＼     \n");
            printf("  ／                ＼   \n");
            printf(" |                    |  \n");
            printf(" |         ★         | \n");
            printf(" |                    |  \n");
            printf("  ＼                ／   \n");
            printf("    ＼            ／     \n");
            printf("      ------------      \n");
            printf("これは一星球だぞ!\nやったなー!きょうのオメーは運がいいぞ～\n");
        break;
        case 1:
            printf("      ____________       \n");
            printf("    ／            ＼     \n");
            printf("  ／                ＼   \n");
            printf(" |      ★            |  \n");
            printf(" |                    | \n");
            printf(" |            ★      |  \n");
            printf("  ＼                ／   \n");
            printf("    ＼            ／     \n");
            printf("      ------------      \n");
            printf("これは二星球だぞ!\nきょうは はめをはずして遊ぶといいみてーだなー\n");
        break;
        case 2:
            printf("      ____________       \n");
            printf("    ／            ＼     \n");
            printf("  ／                ＼   \n");
            printf(" |         ★         |  \n");
            printf(" |                    | \n");
            printf(" |    ★        ★    |  \n");
            printf("  ＼                ／   \n");
            printf("    ＼            ／     \n");
            printf("      ------------      \n");
            printf("これは三星球だぞ!\nきょうは学食に行くとラッキーらしいぞ!\n");
        break;
        case 3:
            printf("      ____________       \n");
            printf("    ／            ＼     \n");
            printf("  ／                ＼   \n");
            printf(" |      ★    ★      |  \n");
            printf(" |                    | \n");
            printf(" |      ★    ★      |  \n");
            printf("  ＼                ／   \n");
            printf("    ＼            ／     \n");
            printf("      ------------      \n");
            printf("これは四星球だぞ!\nやったな!おめえはスーパーラッキーだ!\n今月はずっといいことがあっぞ!\n");
        break;
        
        case 4:
            printf("      ____________       \n");
            printf("    ／            ＼     \n");
            printf("  ／       ★       ＼   \n");
            printf(" |                    |  \n");
            printf(" |     ★      ★     | \n");
            printf(" |                    |  \n");
            printf("  ＼   ★      ★    ／   \n");
            printf("    ＼             ／     \n");
            printf("      ------------      \n");
            printf("これは五星球だぞ!\nたまにはゼニーをつかうといいことあっぞ!\n");
        break;
        case 5:
            printf("      ____________     \n");
            printf("    ／            ＼     \n");
            printf("  ／                ＼   \n");
            printf(" |    ★        ★    |  \n");
            printf(" |         ★         | \n");
            printf(" |    ★        ★    |  \n");
            printf("  ＼                ／   \n");
            printf("    ＼     ★     ／     \n");
            printf("      ------------      \n");
            printf("これは六星球だぞ!\nきょうは歩いて帰るといいことあるみてーだぞ!\n");
        break;
        case 6:
            printf("      ____________      \n");
            printf("    ／            ＼     \n");
            printf("  ／    ★    ★    ＼   \n");
            printf(" |                    |  \n");
            printf(" |    ★   ★   ★     | \n");
            printf(" |                    |  \n");
            printf("  ＼    ★    ★     ／   \n");
            printf("    ＼             ／     \n");
            printf("      ------------      \n");
            printf("これは七星球だぞ!\nラッキーアイテムは仙豆・・・\n");
        break;
        case 7:
            printf("       _____________      \n");
            printf("    ／   ・     ・   ＼     \n");
            printf("  ／  __ ・     ・  __ ＼   \n");
            printf(" |   ＼＼・     ・／／   |  \n");
            printf(" |   | ＼＼     ／／ |   | \n");
            printf(" |   ヽ __・   ・___/    |  \n");
            printf("  ＼  //   _____   //  ／   \n");
            printf("    ＼               ／     \n");
            printf("       -------------     \n");
            printf("ありゃクリリンだな\nおめえ 20年後ハゲちまうぞww\n");
        break;
        case 8:
            printf("       ___________      \n");
            printf("     （___________)       \n");
            printf("    ／             ＼       \n");
            printf("  ／       ／＼      ＼    \n");
            printf(" |       ／ 仙 ＼      |  \n");
            printf(" |      <        >     | \n");
            printf(" |       ＼ 豆 ／      |  \n");
            printf("  ＼       ＼／      ／   \n");
            printf("    ＼             ／     \n");
            printf("       ------------      \n");
            printf("やったぁー仙豆だー－－!!!!\nおめえ けがしてねーならオラが食っちまうぞ!\n");
        break;
        case 9:
            printf("       ______________       \n");
            printf("     ／___        ___＼     \n");
            printf("   ／     ＼____／     ＼   \n");
            printf(" _|   ____       ____   |_\n");
            printf("|_|  ＼__・＼  ／・_／  |_|\n");
            printf("  |    |    <__>    |   | \n");
            printf("   ＼  |  ,_______, |  ／   \n");
            printf("     ＼|   ＼___／  |／     \n");
            printf("        ------------     \n");
            printf("あれはフリーザだ!\nお前は運が悪いみたいだな 早く帰って寝るんだな!\n");
        break;
        }

        printf("\n１～３の好きな数字を入力してくれ！\n");
        scanf("%d", &x);
      
        if (x == 1){
         printf("                               ____              \n");
         printf("                           _ /   ／              \n");
         printf("                       _/       /                \n");
         printf("                    __/        /_________________\n");
         printf("               /                              _／\n");
         printf("           /                 |                ／    \n");
         printf("         /                   |'|ヽ|/_      ／     \n");
         printf("  _ .. -─'               | ''./' '  ,.!:∠     \n");
         printf("  '''  --.._       ;-‐､｀   |__・ ・|          \n");
         printf("=ﾆ二               |       , r-- ',､-｀      \n");
         printf("          -=.二    '-t       ` 一',.'           \n ");
         printf("                        '' ''ｰ- '                \n");
         printf("\nまた遊んでくれよな!じゃあな!\n");
        }else if (x == 2){
         printf("             _______         \n");
         printf("        ,.   ''      ヽ|-一‐､\n");
         printf("    ／                       |\n");
         printf("   /            ,..___.        |\n");
         printf("  /              //|ヽ!        |\n");
         printf(" /    _____|__|  _|_  |       |\n");
         printf(" |  .r--Y / '     ' '`' 7  ／'\n");
         printf("  ''  |'|. ||___･  ・__| /  |\n");
         printf("       ､__.!// ,--^--,// /--'\n");
         printf("            、 ＼___／,.'\n");
         printf("\nまた遊んでね～バイバイ!\n");
        }else if (x == 3){ 
         printf("                                                             _______________\n");
         printf("「` ､　         (ド)(ラ)(ゴ)(ン)(ボ)(ー)(ル)(占)(い)（完）　/             ／\n");
         printf(" |    ＼|⌒ ､ _                               ___  __      /  ____      ／\n");
         printf(" L     ` 、　ヽ￣|,,r  ⌒` ,.┌､ ┌-.__    /￣￣|  | | |    /  ／_／   ／\n");
         printf(" |   !ヽ |0 _|}  |  r  ﾆ､_,/ |ヽ|   |￣  `,_   ! | | |   |／ ＜    ／      _\n");
         printf("  |  |.ノ/  <    |（ |__,r ｰ 、　   |  D ノ|}  | | | |__     ／    ＞   ／ /\n");
         printf("  |    /  ヽ_|] | `ー＿　（ ☆ :）  |  D `, .,   |  |_|__| ／    ／   ／  /\n");
         printf("  L,,／|,,_|ヽ__>`ｰ  ､＿/`|ｰ: _|、__j____ノ_|L_| _____|  ／_______￣￣___/\n");
        }else{
            printf("\nオラ１～３っていったよなー？\n");
        }
}
