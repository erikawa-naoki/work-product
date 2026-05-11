
# Qiskitローカル導入

QiskitをGoogle colabで実行するのが手間な場合ローカルに導入することをおすすめします． 

## 方法1（Windows, Anaconda）

1. Anacondaをインストール 
   Get Startedからやってください．
2. Anacondaを起動，環境作成
   Anacondaを起動．
   
3. 左側にあるEnvironmentsをクリック．
4. 下部中央やや左くらいにあるCreateをクリック．
5. PackagesがPython（3.12くらいがおすすめ）になっていることを確認し，Name（仮想環境の名前）を入力．
6. インストールが終わったら環境一覧にある一つ前で入力した環境の名前をクリック，再生ボタンが出てきたらクリック．Open Terminalをクリック．
7. ターミナルが出てきたら以下のコマンドを入力．
8. 
pip install qiskit:
pip install qiskit_aer
pip install qiskit-ibm-runtime
pip install qiskit-addon-cutting
pip install qiskit[visualization]
pip install jupyter
終了．

9. VScodeでの実行
  VScodeを起動．
10. .ipynb形式のファイルを開く．
11. 右上にあるSelect Kernelをクリック．
12. Pyhton Environments...をクリック．
13. 作成した環境を選択．
プログラムの実行が可能になる．
