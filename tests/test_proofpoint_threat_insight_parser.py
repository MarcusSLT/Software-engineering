from __future__ import annotations

from datetime import datetime, timezone
import unittest

from ti_framework.domain.models import IndexEntry, PreprocessedData
from ti_framework.infrastructure.parsers.proofpoint_threat_insight_parser import ProofpointThreatInsightParser


INDEX_HTML = """
<html>
  <body>
    <main>
      <article>
        <h2><a href="/us/blog/threat-insight/security-brief-threat-actors-gift-holiday-lures-threat-landscape">Security Brief: Threat Actors Gift Holiday Lures to Threat Landscape</a></h2>
      </article>
      <article>
        <h2><a href="/us/blog/threat-insight/call-it-what-you-want-threat-actor-delivers-highly-targeted-multistage-polyglot">Call It What You Want: Threat Actor Delivers Highly Targeted Multistage Polyglot Malware</a></h2>
      </article>
      <a href="/us/blog/threat-insight">Threat Insight</a>
    </main>
  </body>
</html>
"""

ENTRY_HTML = """
<html>
  <body>
    <main>
      <article>
        <h1>Call It What You Want: Threat Actor Delivers Highly Targeted Multistage Polyglot Malware</h1>
        <p>Intro paragraph.</p>
        <h3>Indicators of compromise</h3>
        <table>
          <tr><th>Indicator</th><th>Type</th><th>Context</th><th>First Seen</th></tr>
          <tr><td>indicelectronics[.]net</td><td>Domain</td><td>Delivery</td><td>October 2024</td></tr>
          <tr><td>46.30.190[.]96</td><td>IP</td><td>Delivery</td><td>October 2024</td></tr>
          <tr><td>336d9501129129b917b23c60b01b56608a444b0fbe1f2fdea5d5beb4070f1f14</td><td>SHA256</td><td>OrderList.zip</td><td>October 2024</td></tr>
          <tr><td>bokhoreshonline[.]com</td><td>Domain</td><td>C2</td><td>October 2024</td></tr>
        </table>
        <h2>ET rules</h2>
        <p>Stop here.</p>
      </article>
    </main>
  </body>
</html>
"""


ENTRY_HTML_FALLBACK_TABLE = """
<html>
  <body>
    <article class="node--type--blog-post">
      <div class="node-full__body blog-content__body">
        <h3>Why it matters</h3>
        <p>Intro paragraph.</p>
        <table>
          <tr><td><strong>Indicator</strong></td><td><strong>Description</strong></td><td><strong>First Seen</strong></td></tr>
          <tr><td>alice@example[.]com</td><td>Sender Email</td><td>06 March 2026</td></tr>
          <tr><td>121[.]127[.]232[.]253:8443</td><td>Information Stealer C2</td><td>06 March 2026</td></tr>
          <tr><td>d338a7f85737cac1a7b4b5a1cca94e33d0aa8260548667c6733225d4c20cb848</td><td>Information Stealer SHA256</td><td>06 March 2026</td></tr>
          <tr><td>hxxps://www[.]upsystems[.]one/Alex[.]exe</td><td>Payload URL</td><td>06 March 2026</td></tr>
          <tr><td>bksgcefzqyb[.]com</td><td>Phishing Landing Domain</td><td>25 February 2026</td></tr>
        </table>
      </div>
    </article>
  </body>
</html>
"""
ENTRY_HTML_EXAMPLE = """
<html>
  <body>
    <main>
      <article>
        <h1>Security Brief: Threat Actors Gift Holiday Lures to Threat Landscape</h1>
        <div>
          <h3>Example indicators of compromise</h3>
          <p>713d2cca841c2d3df5ba1a4f8926970966ff931d01616ac48d5170a69c1e0765 SHA256 18 November 2024</p>
          <p>cybelejack9[.]mywire[.]org Remcos C2 18 November 2024</p>
          <p>185.161.251[.]208 Sign-In SystemFacing IP, SakaiPages 13 December 2024</p>
          <h2>Previous Blog Post</h2>
        </div>
      </article>
    </main>
  </body>
</html>
"""


class ProofpointThreatInsightParserTest(unittest.TestCase):
    def setUp(self) -> None:
        self.parser = ProofpointThreatInsightParser()
        self.now = datetime.now(timezone.utc)

    def test_parse_index_extracts_publication_links(self) -> None:
        data = PreprocessedData(
            collected_at=self.now,
            source_url="https://www.proofpoint.com/us/blog/threat-insight",
            source_name="Proofpoint Threat Insight",
            snapshot_kind="index",
            text=INDEX_HTML,
            snapshot_locator="memory://index",
        )

        entries = self.parser.parse_index(data)

        self.assertEqual(len(entries), 2)
        self.assertEqual(
            entries[0].publication_url,
            "https://www.proofpoint.com/us/blog/threat-insight/security-brief-threat-actors-gift-holiday-lures-threat-landscape",
        )
        self.assertEqual(
            entries[1].publication_url,
            "https://www.proofpoint.com/us/blog/threat-insight/call-it-what-you-want-threat-actor-delivers-highly-targeted-multistage-polyglot",
        )

    def test_parse_entry_extracts_iocs_from_table(self) -> None:
        data = PreprocessedData(
            collected_at=self.now,
            source_url="https://www.proofpoint.com/us/blog/threat-insight/call-it-what-you-want-threat-actor-delivers-highly-targeted-multistage-polyglot",
            source_name="Proofpoint Threat Insight",
            snapshot_kind="entry",
            text=ENTRY_HTML,
            snapshot_locator="memory://entry",
        )
        index_entry = IndexEntry(
            title="Call It What You Want: Threat Actor Delivers Highly Targeted Multistage Polyglot Malware",
            publication_url=data.source_url,
            source_name="Proofpoint Threat Insight",
            index_source_url="https://www.proofpoint.com/us/blog/threat-insight",
            indexed_at=self.now,
        )

        entry = self.parser.parse_entry(data, index_entry)
        pairs = {(ioc.kind, ioc.value) for ioc in entry.iocs}

        self.assertIn(("domain", "indicelectronics.net"), pairs)
        self.assertIn(("domain", "bokhoreshonline.com"), pairs)
        self.assertIn(("ipv4", "46.30.190.96"), pairs)
        self.assertIn(("sha256", "336d9501129129b917b23c60b01b56608a444b0fbe1f2fdea5d5beb4070f1f14"), pairs)

    def test_parse_entry_extracts_iocs_from_example_section_text(self) -> None:
        data = PreprocessedData(
            collected_at=self.now,
            source_url="https://www.proofpoint.com/us/blog/threat-insight/security-brief-threat-actors-gift-holiday-lures-threat-landscape",
            source_name="Proofpoint Threat Insight",
            snapshot_kind="entry",
            text=ENTRY_HTML_EXAMPLE,
            snapshot_locator="memory://entry-text",
        )
        index_entry = IndexEntry(
            title="Security Brief: Threat Actors Gift Holiday Lures to Threat Landscape",
            publication_url=data.source_url,
            source_name="Proofpoint Threat Insight",
            index_source_url="https://www.proofpoint.com/us/blog/threat-insight",
            indexed_at=self.now,
        )

        entry = self.parser.parse_entry(data, index_entry)
        pairs = {(ioc.kind, ioc.value) for ioc in entry.iocs}

        self.assertIn(("sha256", "713d2cca841c2d3df5ba1a4f8926970966ff931d01616ac48d5170a69c1e0765"), pairs)
        self.assertIn(("domain", "cybelejack9.mywire.org"), pairs)
        self.assertIn(("ipv4", "185.161.251.208"), pairs)

    def test_parse_entry_extracts_iocs_from_indicator_table_without_heading(self) -> None:
        data = PreprocessedData(
            collected_at=self.now,
            source_url="https://www.proofpoint.com/us/blog/threat-insight/security-brief-tax-scams-aim-steal-funds-taxpayers",
            source_name="Proofpoint Threat Insight",
            snapshot_kind="entry",
            text=ENTRY_HTML_FALLBACK_TABLE,
            snapshot_locator="memory://entry-fallback-table",
        )
        index_entry = IndexEntry(
            title="Security Brief: Tax Scams Aim to Steal Funds from Taxpayers",
            publication_url=data.source_url,
            source_name="Proofpoint Threat Insight",
            index_source_url="https://www.proofpoint.com/us/blog/threat-insight",
            indexed_at=self.now,
        )

        entry = self.parser.parse_entry(data, index_entry)
        pairs = {(ioc.kind, ioc.value) for ioc in entry.iocs}

        self.assertNotIn(("domain", "example.com"), pairs)
        self.assertIn(("ipv4", "121.127.232.253"), pairs)
        self.assertIn(("sha256", "d338a7f85737cac1a7b4b5a1cca94e33d0aa8260548667c6733225d4c20cb848"), pairs)
        self.assertIn(("url", "https://www.upsystems.one/Alex.exe"), pairs)
        self.assertIn(("domain", "bksgcefzqyb.com"), pairs)


if __name__ == "__main__":
    unittest.main()
