import unittest

from build import Builder


class MermaidRenderingTest(unittest.TestCase):
    def test_mermaid_fence_becomes_renderable_container(self) -> None:
        rendered = Builder().markdown_renderer().convert(
            "```mermaid\nflowchart LR\n    A --> B\n```"
        )

        self.assertIn('<div class="mermaid">', rendered)
        self.assertIn("flowchart LR", rendered)
        self.assertNotIn('<div class="highlight">', rendered)


if __name__ == "__main__":
    unittest.main()
