#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <sys/socket.h>
#include <sys/types.h>
#include <netinet/in.h>
#include <arpa/inet.h>

/*
 * 数当てゲームのクライアントプログラム
 * 
 * 機能:
 * - サーバーに接続
 * - ユーザーから1-100の数字を入力
 * - 入力された数字をサーバーに送信
 * - サーバーからの応答を表示
 * - "正解！"が返ってくるまで繰り返し
 *
 * 使用方法:
 * 1. コンパイル: gcc -o client client.c
 * 2. 実行: ./client <ホストアドレス> <ポート番号>
 */

int main(int argc, char *argv[]) {
    // 変数の宣言
    int sockfd;                     // ソケットディスクリプタ
    struct sockaddr_in server_addr; // サーバーアドレス構造体
    char buf[BUFSIZ];              // 送受信用バッファ

    // ソケットの作成
    if ((sockfd = socket(PF_INET, SOCK_STREAM, 0)) < 0) {
        perror("socket");
        exit(1);
    }

    // サーバーアドレスの設定
    server_addr.sin_family = PF_INET;
    server_addr.sin_port = htons(atoi(argv[2]));
    if (inet_aton(argv[1], &server_addr.sin_addr) == 0) {
        perror("inet_aton");
        close(sockfd);
        exit(1);
    }

    // サーバーへの接続
    if (connect(sockfd, (struct sockaddr *)&server_addr, sizeof(server_addr)) < 0) {
        perror("connect");
        close(sockfd);
        exit(1);
    }

    printf("ゲーム開始！\n");

    // メインゲームループ
    while (1) {
        // ユーザーからの入力受付
        printf("1～100の数字を入力して: ");
        fgets(buf, BUFSIZ, stdin);
        buf[strcspn(buf, "\n")] = 0;  // 改行文字の削除

        // サーバーにデータを送信
        send(sockfd, buf, strlen(buf), 0);

        // サーバーからの応答を受信
        memset(buf, 0, BUFSIZ);
        recv(sockfd, buf, BUFSIZ, 0);

        // 結果の表示
        printf("サーバ: %s\n", buf);

        // 正解の場合はループを抜ける
        if (strstr(buf, "正解！") != NULL) {
            // 部分一致でよいため"strcmp"ではなく"strstr"を使う
            break;
        }
    }

    // ソケットのクローズ
    close(sockfd);
    return 0;
}
//gcc -o client client.c
//./client 0.0.0.0 6543
