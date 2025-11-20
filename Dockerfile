# 1. 基础镜像
FROM python:3.11-slim

# 2. 设置工作目录
WORKDIR /app

# 3. 安装系统依赖 & PrinceXML
#    注意：我们增加了 curl 和 gdebi-core 用于安装 Prince
RUN apt-get update && \
    apt-get install -y git curl gdebi-core libxml2 libgomp1 fonts-stix && \
    # 下载 PrinceXML (Debian 11/12 通用版)
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