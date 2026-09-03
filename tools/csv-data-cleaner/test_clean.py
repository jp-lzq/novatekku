import csv
import tempfile
import unittest
from pathlib import Path

import clean


class DataCleanerTest(unittest.TestCase):
    def test_encoding_detection(self):
        self.assertEqual(clean.detect_encoding("商品,価格".encode("cp932")), "cp932")
        self.assertEqual(clean.detect_encoding("商品,价格".encode("gb18030")), "gb18030")

    def test_dates_and_amounts(self):
        header = ["date", "amount", "name"]
        rows = [
            ["2026/09/03", "¥218,000", " iPhone 17 "],
            ["2026/09/03", "¥218,000", " iPhone 17 "],
            ["", "", ""],
            ["03/31/2026", "(1,250.50)", "return"],
        ]
        result = clean.clean_table(
            header, rows, date_columns=["date"], amount_columns=["amount"]
        )
        cleaned_header, cleaned_rows, empty_count, duplicate_count = result
        self.assertEqual(cleaned_header, header)
        self.assertEqual(cleaned_rows[0], ["2026-09-03", "218000", "iPhone 17"])
        self.assertEqual(cleaned_rows[1], ["2026-03-31", "-1250.5", "return"])
        self.assertEqual(empty_count, 1)
        self.assertEqual(duplicate_count, 1)

    def test_csv_file(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source.csv"
            source.write_bytes("商品,価格\r\niPhone,176000\r\niPhone,176000\r\n".encode("cp932"))
            result = clean.clean_file(source, directory, amount_columns=["価格"])
            output = Path(result["output"])
            with output.open(encoding="utf-8-sig", newline="") as stream:
                rows = list(csv.reader(stream))
        self.assertEqual(rows, [["商品", "価格"], ["iPhone", "176000"]])
        self.assertEqual(result["duplicates_removed"], 1)

    @unittest.skipIf(clean.Workbook is None, "openpyxl is not installed")
    def test_xlsx_file(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source.xlsx"
            workbook = clean.Workbook()
            sheet = workbook.active
            sheet.append(["date", "amount"])
            sheet.append(["2026年9月3日", "￥10,500"])
            workbook.save(source)
            result = clean.clean_file(
                source, directory, date_columns=["date"], amount_columns=["amount"]
            )
            header, rows = clean.read_xlsx(result["output"])
        self.assertEqual(header, ["date", "amount"])
        self.assertEqual(rows, [["2026-09-03", "10500"]])


if __name__ == "__main__":
    unittest.main()
