import datetime
import os
import shutil
import unittest
from unittest import mock

import arrow
import pandas as pd
from numpy.testing import assert_array_equal

from omega.boards.board import ConceptBoard, IndustryBoard, combined_filter
from tests.boards import (
    concept_members,
    concept_names,
    industry_members,
    industry_names,
)


class BoardTest(unittest.TestCase):
    @mock.patch(
        "boards.board.stock_board_industry_name_ths", return_value=industry_names
    )
    @mock.patch(
        "boards.board.stock_board_industry_cons_ths", side_effect=industry_members
    )
    @mock.patch("boards.board.stock_board_concept_name_ths", return_value=concept_names)
    @mock.patch(
        "boards.board.stock_board_concept_cons_ths", side_effect=concept_members
    )
    def setUp(self, mock_0, mock_1, mock_2, mock_3) -> None:
        shutil.rmtree("/tmp/boards.zarr", ignore_errors=True)
        os.environ["boards_store_path"] = "/tmp/boards.zarr"

        with mock.patch("arrow.now", return_value=arrow.get("2022-05-26")):
            IndustryBoard.close()
            ConceptBoard.close()

            IndustryBoard.init()
            ConceptBoard.init()

            ib = IndustryBoard()
            cb = ConceptBoard()
            assert_array_equal(ib.boards["name"], ["种植业与林业", "种子生产", "其他种植业"])
            assert_array_equal(cb.boards["name"], ["农业种植", "粮食概念", "转基因"])

    def test_get_members(self):
        ib = IndustryBoard()
        actual = ib.get_members("881101")
        exp = ["002041", "600265", "000998", "601118", "600598"]
        self.assertListEqual(exp, actual)

        cb = ConceptBoard()
        actual = cb.get_members("308956")
        exp = ["002041", "002505", "600108", "600300", "000998"]
        self.assertListEqual(actual, exp)

    def test_get_boards(self):
        ib = IndustryBoard()
        actual = ib.get_boards("002041")
        exp = ["881101", "884001"]
        self.assertListEqual(actual, exp)

        cb = ConceptBoard()
        actual = cb.get_boards("002041")
        exp = ["308016", "308956", "300435"]
        self.assertListEqual(actual, exp)

    def test_fuzzy_match_board_name(self):
        ib = IndustryBoard()
        actual = ib.fuzzy_match_board_name("农")
        self.assertIsNone(actual)

        actual = ib.fuzzy_match_board_name("种")
        exp = ["881101", "884001", "884003"]
        self.assertListEqual(exp, actual)

        cb = ConceptBoard()
        actual = cb.fuzzy_match_board_name("基因")
        self.assertListEqual(["300435"], actual)

    def test_get_name(self):
        ib = IndustryBoard()
        cb = ConceptBoard()

        actual = ib.get_name("881101")
        self.assertEqual("种植业与林业", actual)

        actual = cb.get_name("308016")
        self.assertEqual("农业种植", actual)

    def test_get_code(self):
        ib = IndustryBoard()
        cb = ConceptBoard()

        actual = ib.get_code("种植业与林业")
        self.assertEqual("881101", actual)

        actual = cb.get_code("农业种植")
        self.assertEqual("308016", actual)

    def test_filter(self):
        ib = IndustryBoard()
        cb = ConceptBoard()

        in_boards = ["881101", "其他"]
        stocks = ib.filter(in_boards)
        self.assertSetEqual(set({"601118"}), set(stocks))

        in_boards = ["881101", "其他"]
        stocks = ib.filter(in_boards, without=["881101"])
        self.assertSetEqual(set(), set(stocks))

        in_boards = ["308016", "基因"]
        stocks = cb.filter(in_boards)
        self.assertSetEqual(set(["002041", "000998"]), set(stocks))

        stocks = cb.filter(in_boards, without=["308956"])
        self.assertSetEqual(set(), set(stocks))

        stocks = set(ib.filter(["种", "其他种植业"]))
        self.assertSetEqual({"600108", "600540", "600359", "601118", "002772"}, stocks)

        # 顺序不改变结果
        stocks = set(ib.filter(["其他种植业", "种"]))
        self.assertSetEqual({"600108", "600540", "600359", "601118", "002772"}, stocks)

        stocks = set(ib.filter(["种植业", "种子生产"]))
        print(stocks)

    def test_find_new_concept_boards(self):
        cb = ConceptBoard()

        with mock.patch("arrow.now", return_value=arrow.get("2022-05-27")):
            boards = cb.find_new_concept_boards()
            self.assertEqual(boards.loc[0, "code"], "308956")

    @mock.patch("boards.board.stock_board_concept_name_ths", return_value=concept_names)
    @mock.patch(
        "boards.board.stock_board_concept_cons_ths", side_effect=concept_members
    )
    def test_new_members_in_board(self, mock_0, mock_1):
        with mock.patch("arrow.now", return_value=arrow.get("2022-05-27")):
            ConceptBoard.fetch_board_list()
            ConceptBoard.fetch_board_members()

            cb = ConceptBoard()
            members = cb.members_group["20220526"]
            exp = set(members[-3:]["code"])
            cb.members_group["20220526"] = members[:-3]

            stocks = cb.new_members_in_board(1)
            self.assertDictEqual(stocks, {"300435": exp})

    def test_combined_filter(self):
        actual = combined_filter("种植业与林业", ["粮食概念", "转基因"])
        self.assertSetEqual({"000998", "002041"}, actual)
