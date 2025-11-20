# 1. 基础镜像
FROM python:3.11-slim-bookworm

# 2. 设置工作目录
WORKDIR /app

# 3. 安装系统依赖 & PrinceXML & 多套中文字体
RUN apt-get update && \
    # [关键修改] 增加了 fonts-wqy-microhei 和 fonts-wqy-zenhei (双保险)
    apt-get install -y git curl gdebi-core libxml2 libgomp1 fonts-stix fonts-noto-cjk fonts-wqy-microhei fonts-wqy-zenhei && \
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
RUN pip install --no-cache-dir -r requirements.txt

# 5. 复制项目代码
COPY . .

# 6. 启动命令
ENTRYPOINT ["python", "GitReport.py"]