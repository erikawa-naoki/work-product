#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <sys/socket.h>
#include <sys/types.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <pthread.h>
#include <time.h>

/*
・数当てゲームのサーバープログラム
・
・機能:
・- サーバーは1-100の間でランダムな数字を生成
・- 複数のクライアントを同時に処理
・- クライアントからの推測に対して、以下の応答を返す：
・  - 正解の場合: "正解！"
・  - 差が5以内の場合: "おしい！"
・  - 小さすぎる場合: "小さすぎ！"
・  - 大きすぎる場合: "大きすぎ！"
 */

// 定数の定義
#define BUF_SIZE 1024 
#define MAX_CLIENTS 3 

// クライアント処理用スレッド関数
void *thread_client(void *arg) {

    int client_sock = *(int *)arg;
    char buf[BUF_SIZE];
    int secret = rand() % 100 + 1;
    int kaisuu = 0;
    int score;
    free(arg);
    ssize_t bytes_received;

    printf("数字を決定！: %d\n", secret);

    // メインのゲーム
    while (1) {
        // クライアントからデータを受信
        bytes_received = recv(client_sock, buf, BUF_SIZE - 1, 0); 
        // 受信エラーチェック
        if (bytes_received <= 0) {
            printf("クライアントとの接続が終了\n");
            break;
        }

        buf[bytes_received] = '\0';
        // 文字列を数値に変換
        int guess = atoi(buf);
        kaisuu++;

        // 推測値の判定
        if (guess == secret) {
            // 正解時の得点計算
            score = 105 - kaisuu * 5;
            if (score < 0) score = 0;

            // 結果メッセージの作成
            snprintf(buf, BUF_SIZE, "正解！点数: %d (推測回数: %d)\n", score, kaisuu);
            // 結果送信
            send(client_sock, buf, strlen(buf), 0);
            printf("クライアントの接続を終了\n");
            close(client_sock);  
            return NULL; 

        } else if (guess < secret) {
            // 推測が小さい場合の処理
            if  (secret - guess <= 5) {
                strcpy(buf, "おしい！小さい！"); 
            } else {
                strcpy(buf, "小さすぎ！");
            }
        } else {
            // 推測が大きい場合の処理
            if (guess - secret <= 5) {
                strcpy(buf, "おしい！大きい！");
            } else {
                strcpy(buf, "大きすぎ！");
            }
        }

        // 結果をクライアントに送信
        send(client_sock, buf, strlen(buf), 0); 
    }

    // クライアントソケットを閉じる
    close(client_sock);
    return NULL;
}

// メイン関数
int main(int argc, char *argv[]) {

    srand(time(NULL));

    // 変数宣言
    int soc, *new_soc; 
    struct sockaddr_in serv, clnt; 
    socklen_t sin_size; 
    int port;

    // コマンドライン引数チェック
    if (argc != 3) {
        exit(1);
    }

    // サーバーソケットの作成
    if ((soc = socket(PF_INET, SOCK_STREAM, 0)) < 0) { 
        perror("socketエラー"); 
        exit(1);
    }

    // サーバーアドレス構造体の設定
    serv.sin_family = PF_INET; 
    serv.sin_port = htons(atoi(argv[2])); 
    serv.sin_addr.s_addr = INADDR_ANY; 

    // ソケットのバインド
    if (bind(soc, (struct sockaddr *)&serv, sizeof(serv)) < 0) {
        perror("bindエラー"); 
        exit(1);
    }

    // 接続待ちの開始
    if (listen(soc, MAX_CLIENTS) < 0) { 
        perror("listenエラー");
        exit(1);
    }

    // サーバー起動メッセージ
    printf("サーバ起動 %s:%s\n", argv[1], argv[2]); // %s:文字列型データを表示

    // クライアントアドレス構造体のサイズ設定
    sin_size = sizeof(struct sockaddr_in); 

    // クライアント接続受付ループ
    while (1) {
        // 新規クライアントソケット用メモリ確保
        new_soc = malloc(sizeof(int));
        // クライアント接続の受付
        if ((*new_soc = accept(soc, (struct sockaddr *)&clnt, &sin_size)) < 0) {
            perror("acceptエラー");
            free(new_soc);
            continue;
        }

        // 接続クライアントの情報表示
        printf("接続： %s:%d\n", inet_ntoa(clnt.sin_addr), ntohs(clnt.sin_port));

        // クライアント処理用スレッドの作成
        pthread_t thread_id;
        if (pthread_create(&thread_id, NULL, thread_client, new_soc) != 0) {
            perror("pthread_createエラー");
            close(*new_soc); 
            free(new_soc); 
        } else {
            // スレッドのデタッチ
            pthread_detach(thread_id); 
        }
    }

    // サーバーソケットのクローズ
    close(soc);
    return 0;
}
//gcc -o server server.c -lpthread
//./server 0.0.0.0 6543
