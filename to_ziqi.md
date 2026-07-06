# 使用步骤和说明
1. 我把这个工具打包成docker镜像，方便在任何环境直接部署使用。
使用前需要先确保安装了docker。
2. 解压到文件夹，命令如下：
```bash
mkdir video-finder-ziqi
tar -xzf video-finder-ziqi.tar.gz -C video-finder-ziqi
cd video-finder-ziqi
```
3. 正常下一步是添加api key，我这里直接把我用的key打包进去了，你就不用添加了。
4. 构建镜像：
第一次构建镜像会很慢，要安装很多包。耐心等待。
```bash
docker build -t video-finder-ziqi .
```
5. 准备输入和输出目录：
```bash
mkdir -p input_video runs
```
把一个视频放到：
```bash
input_video/视频文件名.mp4
```
6. 运行：记得把命令中的`input.mp4`改成你的视频文件名。
```bash
docker run --rm \
  --env-file .env \
  -v "$PWD/input_video:/data/input_video" \
  -v "$PWD/runs:/app/.video_finder_runs" \
  video-finder-ziqi \
  find /data/input_video/input.mp4 --skip-text-search --ocr-backend paddle --frame-interval 3 --top-k 3
```
7. 补充说明：
   上面的命令只输出结果：3条最接近的候选视频链接。
   如果想看中间步骤和中间结果，在命令的参数里加上`--debug`。
   上面的命令默认跳过了大模型强化过的文字搜索结果（因为相比于搜图这个没啥用。。。）。
   如果想加上这一步，在命令的参数里去掉`--skip-text-search`。
8. 关于api:
   本项目里调用的api，目前都是免费的，但是其中几个有限额，超过限额会收费。
   其中，通过Serpapi调用的Google lens api用于搜图，每个月限额250次。
   YouTube data api用于获取视频信息，每天限额100次。
   LLM暂时用的免费的（反正没啥用。。。）。
   所以注意使用限额，如果有大量使用的需要，可以多准备几个账号白嫖，或者充值（不值得）。
## 
测试效果还好，有的比较准，有的一般。
师姐试一下，后续还可以改。

Chris L