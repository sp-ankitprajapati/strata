import unittest

from extract_reference_candidates import parse_table


class ReferenceTableTests(unittest.TestCase):
    def test_wall_columns_keep_thickness_and_all_scopes(self):
        rows = [
            [
                "シリーズ名", "商品板厚(㎜)",
                "商品名", "塗装種類", "塗装色",
            ],
            ["レジェール", "21", "全て", "全て", "全て"],
        ]

        candidates, rules = parse_table(rows)

        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0]["name"], "レジェール")
        self.assertEqual(
            candidates[0]["thickness_mm_raw"], "21"
        )
        self.assertEqual(candidates[0]["raw_cells"], rows[1])
        self.assertEqual(rules, [])

    def test_roof_merged_rule_is_not_a_product(self):
        rows = [
            ["商品名（塗装色：すべて）", None, None, None],
            ["品名にNEOが入っている物", None, None, None],
            ["レサス", "レサスTX", "リコロニー", "スマートメタル"],
        ]

        candidates, rules = parse_table(rows)

        self.assertEqual(len(candidates), 4)
        self.assertEqual(len(rules), 1)
        self.assertEqual(candidates[0]["row"], 3)
        self.assertEqual(candidates[0]["column"], 1)

    def test_solido_type_keeps_its_group(self):
        candidates, _ = parse_table([
            ["シリーズ名", "商品名", "塗装種類", "塗装色"],
            ["typeF", "全て", "全て", "全て"],
        ])

        self.assertEqual(candidates[0]["group"], "SOLIDO")
        self.assertEqual(candidates[0]["name"], "typeF")

    def test_unknown_layout_requires_attention(self):
        with self.assertRaises(ValueError):
            parse_table([["Unexpected header"], ["Board"]])


if __name__ == "__main__":
    unittest.main()