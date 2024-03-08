FROM python:3.8-slim

# 作業ディレクトリの設定
WORKDIR /chatbot

# 依存関係のコピーとインストール
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# アプリケーションのコードをコピー
COPY . .

# ポートの公開
EXPOSE 8080

# コンテナ起動時に実行されるコマンド
CMD ["python", "app.py"]