from __future__ import annotations

from datetime import datetime, timezone
import unittest

from ti_framework.domain.models import IndexEntry, PreprocessedData
from ti_framework.infrastructure.parsers.securelist_parser import SecurelistParser


INDEX_HTML = """
<html>
  <body>
    <main>
      <h3><a href="https://securelist.com/the-long-road-to-your-crypto-clipbanker/119341/">The long road to your crypto</a></h3>
      <h3><a href="/attacks-on-industrial-enterprises-using-rms-and-teamviewer-new-data/99206/">Attacks on industrial enterprises using RMS and TeamViewer: new data</a></h3>
      <h3><a href="/all/">Archive</a></h3>
    </main>
  </body>
</html>
"""

ENTRY_HTML = """
<html>
  <body>
    <main>
      <article>
        <h1>Attacks on industrial enterprises using RMS and TeamViewer: new data</h1>
        <div class="post-content">
          <p>Intro paragraph.</p>
          <h2>Appendix I – Indicators of Compromise</h2>
          <h3>File Hashes</h3>
          <ul>
            <li>386a1594a0add346b8fbbebcf1547e77</li>
            <li>e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855</li>
          </ul>
          <h3>Domains and IPs</h3>
          <ul>
            <li>timkasprot.temp.swtest[.]ru</li>
            <li>77.222.56[.]169</li>
          </ul>
          <h3>URLs</h3>
          <ul>
            <li>https[:]//example[.]org/path</li>
          </ul>
          <h2>Appendix II – MITRE ATT&amp;CK Mapping</h2>
          <p>Stop here.</p>
        </div>
      </article>
    </main>
  </body>
</html>
"""


class SecurelistParserTest(unittest.TestCase):
    def setUp(self) -> None:
        self.parser = SecurelistParser()
        self.now = datetime.now(timezone.utc)

    def test_parse_index_extracts_publication_links(self) -> None:
        data = PreprocessedData(
            collected_at=self.now,
            source_url="https://securelist.com/all/",
            source_name="Securelist",
            snapshot_kind="index",
            text=INDEX_HTML,
            snapshot_locator="memory://index",
        )

        entries = self.parser.parse_index(data)

        self.assertEqual(len(entries), 2)
        self.assertEqual(entries[0].publication_url, "https://securelist.com/the-long-road-to-your-crypto-clipbanker/119341/")
        self.assertEqual(entries[1].publication_url, "https://securelist.com/attacks-on-industrial-enterprises-using-rms-and-teamviewer-new-data/99206/")

    def test_parse_entry_extracts_basic_iocs(self) -> None:
        data = PreprocessedData(
            collected_at=self.now,
            source_url="https://securelist.com/attacks-on-industrial-enterprises-using-rms-and-teamviewer-new-data/99206/",
            source_name="Securelist",
            snapshot_kind="entry",
            text=ENTRY_HTML,
            snapshot_locator="memory://entry",
        )
        index_entry = IndexEntry(
            title="Attacks on industrial enterprises using RMS and TeamViewer: new data",
            publication_url=data.source_url,
            source_name="Securelist",
            index_source_url="https://securelist.com/all/",
            indexed_at=self.now,
        )

        entry = self.parser.parse_entry(data, index_entry)
        pairs = {(ioc.kind, ioc.value) for ioc in entry.iocs}

        self.assertIn(("md5", "386a1594a0add346b8fbbebcf1547e77"), pairs)
        self.assertIn(("sha256", "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"), pairs)
        self.assertIn(("domain", "timkasprot.temp.swtest.ru"), pairs)
        self.assertIn(("ipv4", "77.222.56.169"), pairs)
        self.assertIn(("url", "https://example.org/path"), pairs)


if __name__ == "__main__":
    unittest.main()
