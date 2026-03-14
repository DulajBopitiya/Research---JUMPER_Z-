# src/logic/highlight_engine.py

import json
import os
from tree_sitter import Parser, Language
import tree_sitter_cpp
from src.core.config import LANGUAGE_CONFIG_PATH


class HighlightEngine:
    def __init__(self):
        config_path = LANGUAGE_CONFIG_PATH

        try:
            self.data = json.loads(config_path.read_text())
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"CRITICAL: Config load error: {e}")
            self.data = {"registers": [], "constants": [], "keywords": []}
            
        # 3. Parser Setup
        cpp_lang = Language(tree_sitter_cpp.language())
        self.parser = Parser(cpp_lang)
         

    def highlight(self, text_widget, code):
        tree = self.parser.parse(code.encode("utf-8"))
        code_bytes = code.encode("utf-8")
        
        # Clear tags
        tags = ["kw", "type", "string", "comment", "number", "func", "preproc", "constant", "register"]
        for tag in tags:
            text_widget.tag_remove(tag, "1.0", "end")
            
        self._traverse(tree.root_node, text_widget, code_bytes)

    def _traverse(self, node, text_widget, code_bytes):
        if node.start_byte != node.end_byte:
            start = f"{node.start_point[0] + 1}.{node.start_point[1]}"
            end = f"{node.end_point[0] + 1}.{node.end_point[1]}"
            node_text = code_bytes[node.start_byte:node.end_byte].decode('utf-8')

            # 1. Keywords (Direct node match)
            if node.type in ("if", "else", "while", "for", "return", "break", "continue", "switch", "case"):
                text_widget.tag_add("kw", start, end)
            
            # 2. Identifiers (Lookup in external JSON data)
            elif node.type == "identifier":
                if node_text in self.data["registers"]:
                    text_widget.tag_add("register", start, end)
                elif node_text in self.data["constants"]:
                    text_widget.tag_add("constant", start, end)
                elif node.parent and node.parent.type in ("function_declarator", "call_expression"):
                    text_widget.tag_add("func", start, end)
                elif node_text in self.data["keywords"]:
                    text_widget.tag_add("kw", start, end)

            # 3. Everything else
            elif node.type == "string_literal": text_widget.tag_add("string", start, end)
            elif node.type == "comment": text_widget.tag_add("comment", start, end)
            elif node.type == "number_literal": text_widget.tag_add("number", start, end)
            elif node.type in ("preproc_include", "preproc_def"): text_widget.tag_add("preproc", start, end)
            elif node.type in ("primitive_type", "type_identifier"): text_widget.tag_add("type", start, end)
            
        for child in node.children:
            self._traverse(child, text_widget, code_bytes)