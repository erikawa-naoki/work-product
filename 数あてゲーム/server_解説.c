#include <stdio.h>
#include <stdlib.h>
#include <string.h> // 文字列操作関数（例: strlen, strcspn, strstr）を使用するため。
#include <unistd.h> //  システムコール（例: close）を使用するため。
#include <sys/socket.h> // ソケット関連の関数（例: socket, connect）を使用するため。
#include <sys/types.h>
#include <netinet/in.h> // ネットワーク構造体（例: struct sockaddr_in）を使用するため。
#include <arpa/inet.h> // IP アドレス変換関数（例: inet_aton）を使用するため。
#include <pthread.h>
#include <time.h>

/*
・数当てゲームのサーバープログラム
・
・機能:
・- サーバーは1-100の間でランダムな数字を生成
・- 複数のクライアントを同時に処理（マルチスレッド対応）
・- クライアントからの推測に対して、以下の応答を返す：
・  - 正解の場合: "正解！"
・  - 差が5以内の場合: "おしい！"
・  - 小さすぎる場合: "小さすぎ！"
・  - 大きすぎる場合: "大きすぎ！"
 */

// 定数の定義
#define BUF_SIZE 1024    // バッファサイズ
#define MAX_CLIENTS 3   // 最大同時接続クライアント数

// クライアント処理用スレッド関数
void *handle_client(void *arg) {
    // クライアントソケットの取得
    int client_sock = *(int *)arg;
    // 引数用メモリの解放
    free(arg);

    // 通信用バッファ
    char buf[BUF_SIZE];
    // 1から100までのランダムな数字を生成
    int secret = rand() % 100 + 1;
    // 推測回数の初期化
    int kaisuu = 0;
    // スコア変数の宣言
    int score;
    // 受信バイト数
    ssize_t bytes_received; // 負の値を扱うためssize_t

    // デバッグ用：生成された数字を表示
    printf("数字を決定！: %d\n", secret);

    // メインゲームループ
    while (1) {
        // クライアントからデータを受信
        bytes_received = recv(client_sock, buf, BUF_SIZE - 1, 0); // recv:ソケットからデータを受信する関数（戻り値-1でエラー）
        // 受信エラーチェック
        if (bytes_received <= 0) {
            printf("クライアントとの接続が終了\n");
            break;
        }

        // 文字列の終端を設定
        buf[bytes_received] = '\0';
        // 文字列を数値に変換
        int guess = atoi(buf); // bufは文字列よりatoiで文字列を整数に変換
        // 推測回数をカウント
        kaisuu++;

        // 推測値の判定
        if (guess == secret) {
            // 正解時の得点計算
            score = 105 - kaisuu * 5;
            // 最低点は0点
            if (score < 0) score = 0;

            // 結果メッセージの作成
            snprintf(buf, BUF_SIZE, "正解！点数: %d (推測回数: %d)\n", score, kaisuu);
            // 結果送信
            send(client_sock, buf, strlen(buf), 0); // len:受信する最大バイト数
            printf("クライアントの接続を終了\n");
            close(client_sock);  // クライアントソケットを閉じる
            return NULL;         // スレッドを終了

        } else if (guess < secret) {
            // 推測が小さい場合の処理
            if  (secret - guess <= 5) {
                strcpy(buf, "おしい！小さい！"); // bufにメッセージを格納して通信するためstrcpyを採用
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
        send(client_sock, buf, strlen(buf), 0); // strlen:strlen(buf) は、C 文字列の長さを計測し、送信すべきデータの長さを正確に指定するために必要
        // buf に格納されるのは C 言語の文字列（char）
    }

    // クライアントソケットを閉じる
    close(client_sock);
    return NULL;
}

// メイン関数
int main(int argc, char *argv[]) {
    // 現在時刻をシード値として乱数を初期化
    srand(time(NULL));

    // 変数宣言
    int soc, *new_soc; // soc:サーバーソケットを格納するための整数型変数, *new_soc:クライアントごとの接続を処理するためのソケットを指すポインタ
    struct sockaddr_in serv, clnt; // sockaddr_in:IPv4 アドレスとポート番号を保持するための構造体
    socklen_t sin_size; // socklen_t:ソケットアドレス構造体のサイズを表す型
    int port;

    /*
    struct sockaddr_in {　16バイト
    short int sin_family;         // アドレスファミリ（AF_INET）
    unsigned short int sin_port;  // ポート番号
    struct in_addr sin_addr;      // IP アドレス
    unsigned char sin_zero[8];    // 構造体のサイズを合わせるために使われる
};
    */

    // コマンドライン引数チェック
    if (argc != 3) {
        exit(1);
    }

    // サーバーソケットの作成
    if ((soc = socket(PF_INET, SOCK_STREAM, 0)) < 0) { // ソケットを作成し成否をチェックする、ソケットが正しく作成されない場合、通信はできない
        perror("socketエラー"); // p"error":直前に発生したエラーのメッセージを標準エラー出力に表示
        exit(1);
    }

    // サーバーアドレス構造体の設定
    serv.sin_family = PF_INET; // PF_INET:Ipv4アドレスを使用することを意味する
    serv.sin_port = htons(atoi(argv[2]));  // htons:ポート番号を「ホストバイトオーダー」から「ネットワークバイトオーダー」に変換, 異なるシステム間でデータを統一するために使用
    serv.sin_addr.s_addr = INADDR_ANY; // INADDR_ANY:0.0.0.0を意味する、サーバーが任意のネットワークインターフェースで接続を受け付けられるように設定

    // ソケットのバインド
    if (bind(soc, (struct sockaddr *)&serv, sizeof(serv)) < 0) { // bind:サーバのソケットを特定の」IPアドレスとポート番号に関連付ける
        perror("bindエラー"); // エラー表示と終了
        exit(1);
    }

    // 接続待ちの開始
    if (listen(soc, MAX_CLIENTS) < 0) { // クライアントの接続待ちをする
        perror("listenエラー");
        exit(1);
    }

    // サーバー起動メッセージ
    printf("サーバ起動 %s:%s\n", argv[1], argv[2]); // %s:文字列型データを表示

    // クライアントアドレス構造体のサイズ設定
    sin_size = sizeof(struct sockaddr_in); // sizeof:指定されたデータ型または構造体のサイズをバイト単位で返す

    // クライアント接続受付ループ
    while (1) {
        // 新規クライアントソケット用メモリ確保
        new_soc = malloc(sizeof(int)); // malloc:メモリ確保関数, 指定したサイズのメモリ領域をヒープ領域から動的に確保し、そのメモリ領域の先頭アドレスを返す
        // クライアント接続の受付
        if ((*new_soc = accept(soc, (struct sockaddr *)&clnt, &sin_size)) < 0) {
            perror("acceptエラー");
            free(new_soc);
            continue;
        }
        /*
        サーバーソケットでクライアントからの接続を受け入れ、接続成功時には新しいソケットファイルディスクリプタを new_soc に格納します。
        */

        // 接続クライアントの情報表示
        printf("Connected from %s:%d\n", inet_ntoa(clnt.sin_addr), ntohs(clnt.sin_port));

        // クライアント処理用スレッドの作成
        // クライアントごとの処理を並行して行うために、スレッドを作成し管理する処理
        pthread_t thread_id; // pthread_t: POSIX スレッドライブラリ（pthread）でスレッドを管理するためのデータ型 thread_id:スレッド識別ID
        if (pthread_create(&thread_id, NULL, handle_client, new_soc) != 0) { // &thread_id:新しく作成されたスレッドのIDを格納するポインタ
            perror("pthread_createエラー");
            close(*new_soc); // クライアントソケットを閉じる
            free(new_soc); // メモリの解放 メモリリークを防ぐ（使用していないメモリを開放することなく確保し続けてしまう現象）＝クラッシュ
        } else {
            // スレッドのデタッチ
            pthread_detach(thread_id); // スレッドの終了を待機しなくて済む
        }
    }

    // サーバーソケットのクローズ
    close(soc);
    return 0;
}
//gcc -o server server.c -lpthread
//./server 0.0.0.0 6543
//工夫点点数をつけた
