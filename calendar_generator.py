#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# カレンダー自動生成ツール
#
# MIT License
# 
# Copyright (c) 2025 [screwyscrew]
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
#
# Description:
#   Python スクリプトで SVG カレンダーを自動生成します。
#   日本の祝日データを取得してカレンダーに反映します。
#
# Usage:
#   python calendar_generator.py
#
# Author:
#   [screwyscrew]
#   (https://github.com/screwyscrew/calendar_generator)
#
import os
import json
import requests
import calendar
import datetime
import textwrap

def find_second_monday(year, month):
    """
    指定した年(year)・月(month)の第2月曜の日付(day)を返す。
    Python では weekday(): 月曜=0, 日曜=6
    """
    d = datetime.date(year, month, 1)
    offset = (7 - d.weekday()) % 7
    first_monday = d + datetime.timedelta(days=offset)
    second_monday = first_monday + datetime.timedelta(days=7)
    return second_monday.day


def get_japanese_holidays_from_web(base_year):
    """
    base_year の祝日データを取得し、さらに「翌年1月」を13月として特別扱いで登録する。
    例: base_year=2025 → 通常の 2025年 の祝日データ + 特別仕様の「2026年1月」を (2025,13,day) に登録
    """
    url = "https://holidays-jp.github.io/api/v1/date.json"
    resp = requests.get(url)
    resp.raise_for_status()
    all_data = resp.json()  # { "YYYY-MM-DD": "祝日名", ... }

    holiday_dict = {}  # {(year, month, day): 祝日名, ...}

    # 1) base_year の祝日を取り込み
    for date_str, holiday_name in all_data.items():
        y_str, m_str, d_str = date_str.split("-")
        y, m, d = int(y_str), int(m_str), int(d_str)
        if y == base_year:
            # "振替休日" の文字列が含まれていれば、holiday_name を強制的に "振替休日" にする
            if "振替休日" in holiday_name:
                holiday_name = "振替休日"
            holiday_dict[(y, m, d)] = holiday_name

    # 2) 翌年1月(=13月) の特別仕様
    next_year = base_year + 1
    holiday_dict[(base_year, 13, 1)] = "元日"
    second_mon_day = find_second_monday(next_year, 1)
    holiday_dict[(base_year, 13, second_mon_day)] = "成人の日"

    return holiday_dict


class CalendarSVGGenerator:
    # A3用紙サイズ
    A3_WIDTH_MM = 297
    A3_HEIGHT_MM = 420

    # 画像配置
    IMG_X = 30
    IMG_Y = 20
    IMG_SIZE = 226

    # フォントサイズ等
    FONT_SIZE_MONTH_MAIN = 36
    FONT_SIZE_DAYOFWEEK_MAIN = 8
    FONT_SIZE_DAY_MAIN = 12
    FONT_SIZE_MONTH_MINI = 10
    FONT_SIZE_DAY_MINI = 4
    FONT_SIZE_HOLIDAY_TEXT = 4

    # メインカレンダー座標
    MAIN_MONTH_X = 45
    MAIN_MONTH_Y = 290
    MAIN_DAYOFWEEK_X = 84
    MAIN_DAYOFWEEK_Y = 270
    MAIN_DAY_X = 84
    MAIN_DAY_Y = 295
    MAIN_COL_INTERVAL_X = 28
    MAIN_ROW_INTERVAL_Y = 19

    # 【変更 1】 stroke-width="0.3" に変更
    DAYOFWEEK_LINE_START = (70, 276)
    DAYOFWEEK_LINE_END   = (266, 276)

    # ミニカレンダー座標
    PREV_MONTH_X = 45
    PREV_MONTH_Y = 305
    PREV_DAY_X = 24
    PREV_DAY_Y = 312
    PREV_COL_INTERVAL_X = 7
    PREV_ROW_INTERVAL_Y = 6

    NEXT_MONTH_X = 45
    NEXT_MONTH_Y = 350
    NEXT_DAY_X = 24
    NEXT_DAY_Y = 357
    NEXT_COL_INTERVAL_X = 7
    NEXT_ROW_INTERVAL_Y = 6

    DAY_OF_WEEK_LABELS = ["SUN", "MON", "TUE", "WED", "THU", "FRI", "SAT"]

    def __init__(self, year):
        self.year = year
        self.holiday_dict = get_japanese_holidays_from_web(self.year)

    def _get_svg_header(self):
        # 【変更 2】 text-before-edge → text-after-edge (あとで <text> の中に適用)
        return textwrap.dedent(f"""\
            <svg
                width="{self.A3_WIDTH_MM}mm"
                height="{self.A3_HEIGHT_MM}mm"
                viewBox="0 0 {self.A3_WIDTH_MM} {self.A3_HEIGHT_MM}"
                xmlns="http://www.w3.org/2000/svg"
                xmlns:xlink="http://www.w3.org/1999/xlink"
                version="1.1"
            >
        """)

    def _get_svg_footer(self):
        return "</svg>"

    def _generate_calendar_svg(self, month):
        svg_parts = []
        svg_parts.append(self._get_svg_header())

        # 実際の「年・月」に変換 (13月→翌年1月)
        actual_year, actual_month = self._interpret_month13(self.year, month)

        # 画像ファイル名
        if month == 13:
            yymm = f"{(self.year + 1) % 100:02d}01"
        else:
            yymm = f"{self.year % 100:02d}{month:02d}"

        jpg_filename = f"{yymm}.jpg"
        image_tag = f"""
            <image
                x="{self.IMG_X}"
                y="{self.IMG_Y}"
                width="{self.IMG_SIZE}"
                height="{self.IMG_SIZE}"
                xlink:href="{jpg_filename}"
            />
        """
        svg_parts.append(textwrap.dedent(image_tag))

        # 月の表示 (ここでは month の値そのまま出している)
        month_to_show = month
        #month_to_show = actual_month  # ←もし実際の月を出したいならこちらにする

        month_text = f"""
            <text
                x="{self.MAIN_MONTH_X}"
                y="{self.MAIN_MONTH_Y}"
                font-family="Franklin Gothic Medium Cond"
                font-size="{self.FONT_SIZE_MONTH_MAIN}"
                text-anchor="middle"
                dominant-baseline="text-after-edge"
            >{month_to_show}</text>
        """
        svg_parts.append(textwrap.dedent(month_text))

        # 曜日ラベル
        for i, wday_label in enumerate(self.DAY_OF_WEEK_LABELS):
            x_pos = self.MAIN_DAYOFWEEK_X + i * self.MAIN_COL_INTERVAL_X
            color = self._get_day_of_week_color(i)
            wday_text = f"""
                <text
                    x="{x_pos}"
                    y="{self.MAIN_DAYOFWEEK_Y}"
                    font-size="{self.FONT_SIZE_DAYOFWEEK_MAIN}"
                    font-family="Franklin Gothic Medium Cond"
                    fill="{color}"
                    text-anchor="middle"
                    dominant-baseline="text-after-edge"
                >{wday_label}</text>
            """
            svg_parts.append(textwrap.dedent(wday_text))

        # lineタグ (stroke-width="0.3" に変更)
        line_tag = f"""
            <line
                x1="{self.DAYOFWEEK_LINE_START[0]}"
                y1="{self.DAYOFWEEK_LINE_START[1]}"
                x2="{self.DAYOFWEEK_LINE_END[0]}"
                y2="{self.DAYOFWEEK_LINE_END[1]}"
                stroke="black"
                stroke-width="0.3"
            />
        """
        svg_parts.append(textwrap.dedent(line_tag))

        # 日付(メイン)
        c = calendar.Calendar(firstweekday=6)
        main_days = [d for d in c.itermonthdates(actual_year, actual_month) if d.month == actual_month]

        def convert_sun_start(wk):
            return (wk + 1) % 7

        first_wday = convert_sun_start(datetime.date(actual_year, actual_month, 1).weekday())

        for d in main_days:
            dday = d.day
            wday = convert_sun_start(d.weekday())
            offset_days = (d - datetime.date(actual_year, actual_month, 1)).days
            row = (offset_days + first_wday) // 7

            x_pos = self.MAIN_DAY_X + wday * self.MAIN_COL_INTERVAL_X
            y_pos = self.MAIN_DAY_Y + row * self.MAIN_ROW_INTERVAL_Y

            color = self._get_day_color(wday, (self.year, month, dday), actual_year, actual_month, mini=False)

            day_text = f"""
                <text
                    x="{x_pos}"
                    y="{y_pos}"
                    font-family="Franklin Gothic Medium Cond"
                    font-size="{self.FONT_SIZE_DAY_MAIN}"
                    fill="{color}"
                    text-anchor="middle"
                    dominant-baseline="text-after-edge"
                >{dday}</text>
            """
            svg_parts.append(textwrap.dedent(day_text))

            # 祝日名
            key3 = (self.year, month, dday)
            if key3 in self.holiday_dict:
                holiday_name = self.holiday_dict[key3]
                holiday_text = f"""
                    <text
                        x="{x_pos}"
                        y="{y_pos + 4}"
                        font-family="Franklin Gothic Medium Cond"
                        font-size="{self.FONT_SIZE_HOLIDAY_TEXT}"
                        fill="orangered"
                        text-anchor="middle"
                        dominant-baseline="text-after-edge"
                    >{holiday_name}</text>
                """
                svg_parts.append(textwrap.dedent(holiday_text))

        # 前後の月(ミニ)
        prev_year, prev_month = self._get_prev_month(self.year, month)
        next_year, next_month = self._get_next_month(self.year, month)

        svg_parts.append(self._get_mini_calendar(
            base_year=prev_year,
            base_month=prev_month,
            month_text_pos=(self.PREV_MONTH_X, self.PREV_MONTH_Y),
            day_start_pos=(self.PREV_DAY_X, self.PREV_DAY_Y),
            col_interval=self.PREV_COL_INTERVAL_X,
            row_interval=self.PREV_ROW_INTERVAL_Y
        ))
        svg_parts.append(self._get_mini_calendar(
            base_year=next_year,
            base_month=next_month,
            month_text_pos=(self.NEXT_MONTH_X, self.NEXT_MONTH_Y),
            day_start_pos=(self.NEXT_DAY_X, self.NEXT_DAY_Y),
            col_interval=self.NEXT_COL_INTERVAL_X,
            row_interval=self.NEXT_ROW_INTERVAL_Y
        ))

        svg_parts.append(self._get_svg_footer())
        return "\n".join(svg_parts)

    def _get_mini_calendar(self, base_year, base_month, month_text_pos, day_start_pos,
                           col_interval, row_interval):
        """
        miniカレンダー用。 base_year, base_month が 13 なら翌年1月扱い。
        """
        (month_x, month_y) = month_text_pos
        (day_x, day_y) = day_start_pos

        part_list = []

        # 実際の (year, month)
        actual_year, actual_month = self._interpret_month13(base_year, base_month)

        # 【変更 3】 ここで表示する月の文字列を {base_month} → {actual_month} に変更
        #  (前回までは base_month をそのまま表示していた)
        month_label_text = f"""
            <text
                x="{month_x}"
                y="{month_y}"
                font-family="Franklin Gothic Medium Cond"
                font-size="{self.FONT_SIZE_MONTH_MINI}"
                text-anchor="middle"
                dominant-baseline="text-after-edge"
            >{actual_month}</text>
        """
        part_list.append(textwrap.dedent(month_label_text))

        c = calendar.Calendar(firstweekday=6)
        mini_days = [d for d in c.itermonthdates(actual_year, actual_month) if d.month == actual_month]

        def convert_sun_start(wk):
            return (wk + 1) % 7

        first_wday = convert_sun_start(datetime.date(actual_year, actual_month, 1).weekday())

        for d in mini_days:
            dday = d.day
            wday = convert_sun_start(d.weekday())
            offset_days = (d - datetime.date(actual_year, actual_month, 1)).days
            row = (offset_days + first_wday) // 7

            x_pos = day_x + wday * col_interval
            y_pos = day_y + row * row_interval

            color = self._get_day_color(wday, (base_year, base_month, dday), actual_year, actual_month, mini=True)
            txt = f"""
                <text
                    x="{x_pos}"
                    y="{y_pos}"
                    font-family="Franklin Gothic Medium Cond"
                    font-size="{self.FONT_SIZE_DAY_MINI}"
                    fill="{color}"
                    text-anchor="middle"
                    dominant-baseline="text-after-edge"
                >{dday}</text>
            """
            part_list.append(textwrap.dedent(txt))

        return "\n".join(part_list)

    def _get_day_of_week_color(self, wday_idx):
        if wday_idx == 0:
            return "orangered"
        elif wday_idx == 6:
            return "royalblue"
        else:
            return "black"

    def _get_day_color(self, wday_idx, base_ymd, actual_year, actual_month, mini=False):
        if base_ymd in self.holiday_dict:
            return "orangered"

        if wday_idx == 0:
            return "orangered"
        elif wday_idx == 6:
            return "royalblue"
        else:
            return "darkslategray" if mini else "black"

    def _interpret_month13(self, base_year, base_month):
        if base_month == 13:
            return (base_year + 1, 1)
        else:
            return (base_year, base_month)

    def _get_prev_month(self, year, month):
        if month == 13:
            return (year, 12)
        elif month == 1:
            return (year - 1, 12)
        else:
            return (year, month - 1)

    def _get_next_month(self, year, month):
        if month == 12:
            return (year, 13)
        elif month == 13:
            return (year + 1, 2)
        else:
            return (year, month + 1)

    def save_calendar_svgs(self, output_dir="."):
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        for m in range(1, 13):
            if m < 13:
                yymm = f"{self.year % 100:02d}{m:02d}"
            else:
                yymm = f"{(self.year + 1) % 100:02d}01"

            filename = os.path.join(output_dir, f"{yymm}.svg")
            svg_str = self._generate_calendar_svg(m)
            with open(filename, "w", encoding="utf-8") as f:
                f.write(svg_str)
            print(f"Saved: {filename}")


if __name__ == "__main__":
    target_year = 2026  # 任意の年を指定
    output_dir = f"cal_svgs_{target_year}"  # 出力先フォルダ名に target_year を反映

    gen = CalendarSVGGenerator(target_year)
    gen.save_calendar_svgs(output_dir=output_dir)
