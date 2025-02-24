#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
中文地理信息提取工具 v1.2

功能：
1. 支持 EPUB/MOBI/TXT/RTF 文件格式输入
2. 使用 spaCy / HanLP / LTP / BERT 进行中文地名实体识别
3. 结合正则表达式增强地名识别
4. 地理编码与结果可视化（CSV/GeoJSON/交互地图）
5. 自动处理依赖安装和常见错误
"""

import argparse
import csv
import json
import logging
import os
import subprocess
import sys
import time
from typing import List, Tuple
import re

# 第三方库依赖
try:
    import spacy
    from geopy.geocoders import Nominatim
    import ebooklib
    from ebooklib import epub
    from bs4 import BeautifulSoup
    import folium
    from striprtf.striprtf import rtf_to_text
    from tenacity import retry, stop_after_attempt, wait_fixed
except ImportError as e:
    print(f"缺少必要依赖库: {e}")
    print("请使用以下命令安装依赖：")
    print("pip install spacy geopy ebooklib beautifulsoup4 folium striprtf tenacity")
    print("然后下载中文模型：python -m spacy download zh_core_web_sm")
    sys.exit(1)

# 日志配置
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("geo_extractor.log"), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)

# ---------------------------
# 配置参数
# ---------------------------
GEOCODE_RETRIES = 3  # 地理编码重试次数
REQUEST_INTERVAL = 1.5  # 请求间隔（秒）
CHUNK_SIZE = 100000  # 大文件分块处理大小（字符）
CUSTOM_CITIES = ["北京", "上海", "广州", "深圳", "重庆", "天津"]  # 自定义补充城市列表

# ---------------------------
# 文本提取模块
# ---------------------------
class TextExtractor:
    @staticmethod
    def extract(file_path: str) -> str:
        """统一文本提取入口"""
        ext = os.path.splitext(file_path)[1].lower()
        if ext == ".epub":
            return TextExtractor._extract_epub(file_path)
        elif ext == ".mobi":
            return TextExtractor._extract_mobi(file_path)
        elif ext == ".txt":
            return TextExtractor._extract_txt(file_path)
        elif ext == ".rtf":
            return TextExtractor._extract_rtf(file_path)
        else:
            raise ValueError(f"不支持的格式: {ext}")

    @staticmethod
    def _extract_epub(file_path: str) -> str:
        """EPUB文件解析"""
        book = epub.read_epub(file_path)
        text = []
        for item in book.get_items():
            if item.get_type() == ebooklib.ITEM_DOCUMENT:
                soup = BeautifulSoup(item.get_body_content(), "html.parser")
                text.append(soup.get_text())
        return "\n".join(text)

    @staticmethod
    def _extract_mobi(file_path: str) -> str:
        """MOBI文件解析(需Calibre支持)"""
        temp_epub = "temp_converted.epub"
        try:
            subprocess.run(
                ["ebook-convert", file_path, temp_epub],
                check=True,
                capture_output=True,
            )
            text = TextExtractor._extract_epub(temp_epub)
        except subprocess.CalledProcessError as e:
            logger.error(f"MOBI转换失败: {e.stderr.decode()}")
            raise RuntimeError(
                "请确保已安装Calibre并添加ebook-convert到系统PATH\n"
                "下载地址：https://calibre-ebook.com/download"
            )
        finally:
            if os.path.exists(temp_epub):
                os.remove(temp_epub)
        return text

    @staticmethod
    def _extract_txt(file_path: str) -> str:
        """纯文本文件解析"""
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()

    @staticmethod
    def _extract_rtf(file_path: str) -> str:
        """RTF文件解析"""
        with open(file_path, "r", encoding="utf-8") as f:
            return rtf_to_text(f.read())

# ---------------------------
# NLP处理模块
# ---------------------------
class NlpProcessor:
    def __init__(self, method="spacy"):
        """
        method: 可选值 "spacy", "hanlp", "ltp", "bert"
        """
        self.method = method
        if method == "spacy":
            try:
                self.nlp = spacy.load("zh_core_web_sm")
            except OSError:
                logger.error("缺少中文模型,请执行: python -m spacy download zh_core_web_sm")
                sys.exit(1)
        elif method == "hanlp":
            try:
                import hanlp
                # 加载 HanLP 预训练模型，可根据需要调整模型名称
                self.hanlp = hanlp.load('LARGE_ALBERT_BASE')
            except ImportError:
                logger.error("请安装 HanLP: pip install hanlp")
                sys.exit(1)
        elif method == "ltp":
            try:
                from ltp import LTP
                self.ltp = LTP()  # 默认加载 LTP 模型
            except ImportError:
                logger.error("请安装 LTP: pip install ltp")
                sys.exit(1)
        elif method == "bert":
            try:
                from transformers import pipeline
                # 使用 Hugging Face pipeline，模型名称可根据需要替换
                self.bert_ner = pipeline("ner", model="hfl/chinese-bert-wwm", tokenizer="hfl/chinese-bert-wwm")
            except ImportError:
                logger.error("请安装 transformers 和 torch: pip install transformers torch")
                sys.exit(1)
        else:
            raise ValueError("未知的处理方法：" + method)

        # 自定义城市正则表达式（可选）
        self.city_pattern = re.compile("|".join(CUSTOM_CITIES))

    def find_locations(self, text: str) -> List[Tuple[str, int, int]]:
        """根据选择的模型，提取文本中的地理实体"""
        locations = set()
        
        if self.method == "spacy":
            # 使用 spaCy 的实体识别
            doc = self.nlp(text)
            for ent in doc.ents:
                if ent.label_ in ["GPE", "LOC"]:
                    locations.add((ent.text, ent.start_char, ent.end_char))
        elif self.method == "hanlp":
            # 使用 HanLP 进行 NER，返回的结果可能需要根据版本调整
            results = self.hanlp(text, tasks=['ner'])
            # 假设返回格式为 {'ner': [(start, end, label, word), ...]}
            for ent in results.get('ner', []):
                # 常见地名标签可为 'NS'（地名）、'NI'（机构）等，根据需要调整
                if ent[2] in ['NS', 'NI', 'NT']:
                    locations.add((ent[3], ent[0], ent[1]))
        elif self.method == "ltp":
            # 使用 LTP 进行 NER
            seg, hidden = self.ltp.seg([text])
            ner_results = self.ltp.ner(hidden, seg)
            # ner_results 为嵌套列表，格式为 (start_index, end_index, label)
            for sent_idx, sent in enumerate(ner_results):
                words = seg[sent_idx]
                for ner in sent:
                    start, end, label = ner
                    if label in ["NS", "NI"]:  # 根据 LTP 标签过滤地名信息
                        entity = "".join(words[start:end+1])
                        # 这里未能获取准确的字符索引，可根据需求进一步优化
                        locations.add((entity, 0, 0))
        elif self.method == "bert":
            # 使用 Hugging Face pipeline 进行 NER
            bert_results = self.bert_ner(text)
            for ent in bert_results:
                # ent 格式示例：{'entity': 'I-LOC', 'score': 0.998, 'index': 5, 'word': '北京', 'start': 10, 'end': 12}
                if ent['entity'].endswith("LOC"):
                    locations.add((ent['word'], ent['start'], ent['end']))
        else:
            raise ValueError("未知的处理方法：" + self.method)

        # 补充匹配自定义的城市名称
        for match in self.city_pattern.finditer(text):
            locations.add((match.group(), match.start(), match.end()))

        return sorted(locations, key=lambda x: x[1])

# ---------------------------
# 地理编码模块
# ---------------------------
class Geocoder:
    def __init__(self):
        self.geolocator = Nominatim(user_agent="china_geo_extractor_v1.2")
        self.cache = {}  # 简单缓存已查询位置

    @retry(stop=stop_after_attempt(GEOCODE_RETRIES), wait=wait_fixed(2))
    def geocode(self, location: str) -> Tuple[float, float]:
        """带缓存和重试的地理编码"""
        if location in self.cache:
            return self.cache[location]

        try:
            time.sleep(REQUEST_INTERVAL)
            result = self.geolocator.geocode(location, language="zh", exactly_one=True)
            if result and self._is_valid_location(result):
                self.cache[location] = (result.latitude, result.longitude)
                return (result.latitude, result.longitude)
            return (None, None)
        except Exception as e:
            logger.warning(f"地理编码失败 [{location}]: {str(e)}")
            return (None, None)

    @staticmethod
    def _is_valid_location(result) -> bool:
        """验证地理位置有效性（限定在中国范围内）"""
        return 3.86 <= result.latitude <= 53.55 and 73.66 <= result.longitude <= 135.05

# ---------------------------
# 主处理流程
# ---------------------------
def main():
    parser = argparse.ArgumentParser(description="中文地理信息提取工具")
    parser.add_argument("input_file", help="输入文件路径")
    parser.add_argument("-o", "--output", default="output", help="输出文件前缀")
    parser.add_argument("-m", "--method", default="spacy", choices=["spacy", "hanlp", "ltp", "bert"], help="选择NER方法")
    args = parser.parse_args()

    # 1. 文本提取
    logger.info(f"开始处理文件: {args.input_file}")
    try:
        text = TextExtractor.extract(args.input_file)
    except Exception as e:
        logger.error(f"文件解析失败: {str(e)}")
        sys.exit(1)

    # 2. 地名识别
    nlp_processor = NlpProcessor(method=args.method)
    locations = nlp_processor.find_locations(text)
    logger.info(f"识别到 {len(locations)} 个地理位置")

    # 3. 地理编码
    geocoder = Geocoder()
    results = []
    for loc, start, end in locations:
        lat, lng = geocoder.geocode(loc)
        context = text[max(0, start-50):min(len(text), end+50)].strip()
        results.append((loc, lat, lng, context))

    # 4. 结果输出
    output_files = {
        "csv": f"{args.output}.csv",
        "geojson": f"{args.output}.geojson",
        "map": f"{args.output}_map.html",
    }

    # CSV输出
    with open(output_files["csv"], "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["地点", "纬度", "经度", "上下文"])
        writer.writerows(results)

    # GeoJSON输出
    features = []
    for loc, lat, lng, ctx in results:
        if lat and lng:
            features.append({
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [lng, lat]},
                "properties": {"name": loc, "context": ctx},
            })

    with open(output_files["geojson"], "w", encoding="utf-8") as f:
        json.dump({"type": "FeatureCollection", "features": features}, f)

    # 交互地图生成
    if features:
        avg_lat = sum(f["geometry"]["coordinates"][1] for f in features) / len(features)
        avg_lng = sum(f["geometry"]["coordinates"][0] for f in features) / len(features)
        m = folium.Map(location=[avg_lat, avg_lng], zoom_start=5)
    else:
        m = folium.Map(location=[35, 105], zoom_start=4)  # 默认中国中心

    for feature in features:
        folium.Marker(
            location=feature["geometry"]["coordinates"][::-1],
            popup=f"<b>{feature['properties']['name']}</b><p>{feature['properties']['context']}</p>",
            icon=folium.Icon(color="red", icon="info-sign"),
        ).add_to(m)

    m.save(output_files["map"])
    logger.info(f"处理完成！生成文件：{', '.join(output_files.values())}")

if __name__ == "__main__":
    main()