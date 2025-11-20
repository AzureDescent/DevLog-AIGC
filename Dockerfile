# 1. 基础镜像
FROM python:3.11-slim-bookworm

# 2. 设置工作目录
WORKDIR /app

# 3. 安装系统依赖 & PrinceXML & 多套中文字体 & Emoji
# [优化] 1. 替换为阿里云镜像源 (解决 502 报错)
# [优化] 2. 增加 --fix-missing 参数 (防止丢包导致的失败)
RUN sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list.d/debian.sources && \
    apt-get update && \
    apt-get install -y --fix-missing \
    git curl gdebi-core libxml2 libgomp1 fonts-stix \
    fonts-noto-cjk fonts-wqy-microhei fonts-wqy-zenhei fonts-noto-color-emoji && \
    # 下载 PrinceXML
    curl -O https://www.princexml.com/download/prince_15.3-1_debian12_amd64.deb && \
    # 安装 PrinceXML
    gdebi --n prince_15.3-1_debian12_amd64.deb && \
    # 清理垃圾
    rm prince_15.3-1_debian12_amd64.deb && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# 4. 复制依赖清单并安装
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 5. 复制项目代码
COPY . .

# 6. 启动命令
ENTRYPOINT ["python", "GitReport.py"]