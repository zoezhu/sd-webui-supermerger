# SuperMerger
- Model merge extention for [AUTOMATIC1111's stable-diffusion-webui](https://github.com/AUTOMATIC1111/stable-diffusion-webui) 
- Merge models can be loaded directly for generation without saving

# Recent Update
すべての更新履歴は[こちら](https://github.com/hako-mikan/sd-webui-supermerger/blob/main/changelog.md)にあります。  
All updates can be found [here](https://github.com/hako-mikan/sd-webui-supermerger/blob/main/changelog.md).

### English / 日本語
English: [![jp](https://img.shields.io/badge/lang-English-green.svg)](https://github.com/hako-mikan/sd-webui-supermerger/blob/main/README.md)

## Updates
- 機能更新, コサイン類似度を用いた最適値計算機能を強化しました[詳細](https://github.com/hako-mikan/sd-webui-supermerger/blob/main/calcmode_en.md#cosine)
- 新機能, 新しいマージ方式tensorを導入しました [詳細](https://github.com/hako-mikan/sd-webui-supermerger/blob/main/calcmode_en.md#tensor)
- XYプロットに新しい軸タイプを追加しました : calcmode,prompt

一部LoRA関係の機能を使用する場合diffusers(0.10.2以降),sklearnが必要です。
# 

# 概要
このextentionではモデルをマージした際、保存せずに画像生成用のモデルとして読み込むことができます。
これまでマージしたモデルはいったん保存して気に入らなければ削除するということが必要でしたが、このextentionを使うことでHDDやSSDの消耗を防ぐことができます。

# 各種設定
## マージモード
### Weight sum
通常のマージです。alphaが使用されます。α=0の場合Model A, α=1 の時model Bになります。
### Add difference
差分マージです。
### Triple sum
マージを3モデル同時に行います。alpha,betaが使用されます。モデル選択窓が3つあったので追加した機能ですが、ちゃんと動くようです。MBWでも使えます。それぞれMBWのalpha,betaを入力してください。
### sum Twice
Weight sumを2回行います。alpha,betaが使用されます。MBWモードでも使えます。それぞれMBWのalpha,betaを入力してください。

### use MBW
チェックするとブロックごとのマージ(階層マージ)が有効になります。各ブロックごとの比率は下部のスライダーかプリセットで設定してください。

### 計算手法(calcmode)
cosineを選択すると、設定されたマージ比率を中心として、コサイン類似度を用いた比較を行い、マージによるロスをなくすような比率を計算し、その比率を用いてマージを行います。
詳しくは下記を参照して下さい(英語です)  
考案された[recoilme](https://github.com/recoilme)氏とこの手法を紹介し最適化してくれた[SwiftIllusion](https://github.com/SwiftIllusion)氏に感謝します。  
https://github.com/hako-mikan/sd-webui-supermerger/issues/33  
https://github.com/recoilme/losslessmix

### 保存
save metadataを有効にするとマージ条件をメタデータとして埋め込めます。safetensor形式のみ有効です。埋め込まれた条件はMetadataタブで確認できます。

## 各ボタン
### Merge
マージした後、生成用モデルとして読み込みます。 __左上のモデル情報とは違うモデルがロードされていることに注意してください。__ 左上のモデル選択画面でモデルを選択しなおすとリセットされます

### Gen
text2imageタブの設定で画像生成を行います

### Merge and Gen
マージしたのち画像を生成します

### Set from ID
マージログから設定を読み込みます。ログはマージが行われるたびに更新され、1から始まる連番のIDが付与されます。IDを生成される画像やPNG infoに記載することも可能で、write merged model ID toから設定してください。-1でSetをすると最後にマージした設定を読み出します。マージログはextention/sd-webui-supermerger/mergehistory.csvに保存されます。他アプリで開いた状態だと読み取りエラーを起こすので注意してください。Historyタブで閲覧や検索が可能です。検索は半角スペースで区切ることでand/or検索が可能です。

## Hires-fix,batch size
Hires-fixを有効化できます。batch sizeを変更できます。batch sizeはXY plotでは無効化されます。

## Elemental merge
[こちら](https://github.com/hako-mikan/sd-webui-supermerger/blob/main/elemental_ja.md)を参照して下さい。

## Sequential XY Merge and Generation
連続マージ画像生成を行います。すべてのマージモードで有効です。
### alpha,beta
アルファ、ベータを変更します。tensorモードでも有効です。
### alpha and beta
アルファ、ベータを同時に変更します。アルファ、ベータの間は半角スペースで区切り、各要素はカンマで区切ってください。数字ひとつの場合はアルファベータ共に同じ値が入力されます。tensorモードでも有効です。  
例: 0,0.5 0.1,0.3 0.4,0.5
### MBW
階層マージを行います。改行で区切った比率を入力してください。プリセットも使用可能ですが、**改行で区切る**ことに注意をして下さい。Triple,Twiceの場合は２行で１セットで入力して下さい。奇数行だとエラーになります。
### seed
シードを変更します。-1と入力すると、反対の軸方向には固定されたseedになります。
### model_A,B,C
モデルを変更します。モデル選択窓で選択されたモデルは無視されます。
### pinpoint blocks
MBWにおいて特定のブロックのみを変化させます。反対の軸はalphaまたはbetaを選んでください。ブロックIDを入力すると、そのブロックのみalpha(beta)が変わります。他のタイプと同様にカンマで区切ります。スペースまたはハイフンで区切ることで複数のブロックを同時に変化させることもできます。最初にNOTをつけることで変化対象が反転します。NOT IN09-OUT02とすると、IN09-OUT02以外が変化します。NOTは最初に入力しないと効果がありません。
#### 入力例
IN01,OUT10 OUT11, OUT03-OUT06,OUT07-OUT11,NOT M00 OUT03-OUT06
この場合
- 1:IN01のみ変化
- 2:OUT10およびOUT11が変化
- 3:OUT03からOUT06が変化
- 4:OUT07からOUT11が変化
- 5:M00およびOUT03からOUT06以外が変化  

となります。0の打ち忘れに注意してください。
![xy_grid-0006-2934360860 0](https://user-images.githubusercontent.com/122196982/214343111-e82bb20a-799b-4026-8e3c-dd36e26841e3.jpg)

ブロックID(大文字のみ有効)
BASE,IN00,IN01,IN02,IN03,IN04,IN05,IN06,IN07,IN08,IN09,IN10,IN11,M00,OUT00,OUT01,OUT02,OUT03,OUT04,OUT05,OUT06,OUT07,OUT08,OUT09,OUT10,OUT11

### calcmode
計算方式を変更します。適用できるマージモードとの対応に注意して下さい。カンマで区切ります

### prompt
プロンプトを変更できます。txt2imgのプロンプトは無視されます。ネガティブプロンプトは有効です。
**改行で区切る**ことに注意をして下さい。

### XYプロットの予約
Reserve XY plotボタンはすぐさまプロットを実行せず、ボタンを押したときの設定のXYプロットの実行を予約します。予約したXYプロットは通常のXYプロットが終了した後か、ReservationタブのStart XY plotボタンを押すと実行が開始されます。予約はXYプロット実行時・未実行時いつでも可能です。予約一覧は自動更新されないのでリロードボタンを使用してください。エラー発生時はそのプロットを破棄して次の予約を実行します。すべての予約が終了するまで画像は表示されませんが、Finishedになったものについてはグリッドの生成は終わっているので、Image Browser等で見ることが可能です。  
「|」を使用することで任意の場所で予約へ移動することも可能です。  
0.1,0.2,0.3,0.4,0.5|0.6,0.7,0.8,0.9,1.0とすると  

0.1,0.2,0.3,0.4,0.5  
0.6,0.7,0.8,0.9,1.0  
というふたつの予約に分割され実行されます。これは要素が多すぎてグリッドが大きくなってしまう場合などに有効でしょう。

### キャッシュについて
モデルをメモリ上に保存することにより連続マージなどを高速化することができます。
キャッシュの設定はweb-uiのsettingから行ってください。

### unloadボタン
現在ロードされているモデルを消去します。これはkohya-ssのGUIを使用するときなどGPUメモリを開放するときに使用します。消去すると画像の生成はできません。生成する場合にはモデルを選び直して下さい。

## LoRA
LoRA関連の機能です。基本的にはkohya-ssのスクリプトと同じですが、階層マージに対応します。現時点ではV2.X系のマージには対応していません。

注意：LyCORISは構造が特殊なため単独マージのみに対応しています。単独マージの比率は1,0のみ使用可能です。他の値を用いるとsame to Strengthでも階層LoRAの結果と一致しません。
LoConは整数以外でもそれなりに一致します。

### merge to checkpoint
モデルにLoRAをマージします。複数のLoRAを同時にマージできます。  
LoRA名1:マージ比率1:階層,LoRA名2:階層,マージ比率2,LoRA名3:マージ比率3･･･  
と入力します。LoRA単独でも使用可能です。「:階層」の部分は無くても問題ありません。比率はマイナスを含めどんな値でも入力できます。合計が１にならないといけないという制約もありません(もちろん大きく1を越えると破綻します)。

### Make LoRA
ふたつのモデルの差分からLoRAを生成します。
demensionを指定すると指定されたdimensionで作製されます。無指定の場合は128で作製します。
alphaとbetaによって配合比率を調整することができます。(alpha x Model_A - beta x Model B)　alpha, beta = 1が通常のLoRA作成となります。

#### google colab使用時の問題
colabで使用する場合に多くのエラーが発生することが報告されています。これは複数の原因によって発生しているようです。  
まずはメモリの問題です。モデルはfp16モデルを使用することを推奨します。フルモデルを使用した場合8GB以上のメモリが必要になります。これはこのスクリプトが使用する量です。また、インストールされているdiffusersのバージョンが異なるとエラーが発生するようです。version 0.10.2で動作確認されています。

### merge LoRAs
ひとつまたは複数のLoRA同士をマージします。kohya-ss氏の最新のスクリプトを使用しているので、dimensionの異なるLoRA同氏もマージ可能ですが、dimensionの変換の際はLoRAの再計算を行うため、生成される画像が大きく異なる可能性があることに注意してください。  

calculate dimentionボタンで各LoRAの次元を計算して表示・ソート機能が有効化します。計算にはわりと時間がかかって、50程度のLoRAでも数十秒かかります。新しくマージされたLoRAはリストに表示されないのでリロードボタンを押してください。次元の再計算は追加されたLoRAだけを計算します。

### 通常マージとsame to Strengthの違い
same to Strengthオプションを使用しない場合は、kohya-ss氏の作製したスクリプトのマージと同じ結果になります。この場合、下図のようにWeb-ui上でLoRAを適用した場合と異なる結果になります。これはLoRAをU-netに組み込む際の数式が関係しています。kohya-ss氏のスクリプトでは比率をそのまま掛けていますが、適用時の数式では比率が２乗されてしまうため、比率を1以外の数値に設定すると、あるいはマイナスに設定するとStrength（適用時の強度）と異なる結果となります。same to Strengthオプションを使用すると、マージ時には比率の平方根を駆けることで、適用時にはStrengthと比率が同じ意味を持つように計算しています。また、マイナスが効果が出るようにも計算しています。追加学習をしない場合などはsame to Strengthオプションを使用しても問題ないと思いますが、マージしたLoRAに対して追加学習をする場合はだれも使用しない方がいいかもしれません。  
下図は通常適用/same to Strengthオプション/通常マージの各場合の生成画像です。figma化とukiyoE LoRAのマージを使用しています。通常マージの場合はマイナス方向でも２乗されてプラスになっていることが分かります。
![xyz_grid-0014-1534704891](https://user-images.githubusercontent.com/122196982/218322034-b7171298-5159-4619-be1d-ac684da92ed9.jpg)

階層別マージについては下記を参照してください

https://github.com/bbc-mc/sdweb-merge-block-weighted-gui

このスクリプトではweb-ui、mbw-merge、kohya-ssのスクリプトを一部使用しています
