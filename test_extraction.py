"""Regression coverage for the DOM extraction contract (no public site required)."""
import unittest

from playwright.async_api import async_playwright

from test_playwright import extract_page_data, is_internal_link


FIXTURE = """
<nav><a href="/nav">Navigation</a></nav>
<main><section id="intro"><h1>Editorial heading</h1><p>Useful editorial copy.</p>
  <ul><li>First point</li><li>Second point</li></ul>
  <a class="button" href="/contact">Talk to an expert</a>
</section><section id="secondary"><a class="button" href="/contact">Talk to an expert</a></section>
<section class="faq accordion"><button aria-expanded="false">What is covered?</button><p>FAQ answer.</p></section>
<form id="contact"><div class="form-group"><label for="email">Work email *</label><input id="email" name="email"></div>
  <label>Native required * <input name="native" required></label>
  <label for="role">Role *</label><select id="role" name="role"><option value="">Choose</option><option value="qa">QA</option></select>
  <label for="cv">CV</label><input id="cv" name="cv" type="file" accept=".pdf,.docx" multiple>
  <input type="hidden" name="g-recaptcha-response"><button type="submit">Send</button></form>
<a href="https://external.example/path">External resource</a></main>
<footer><p>Footer noise</p><a href="/terms">Terms</a></footer>
"""


class ExtractionTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=True)
        self.page = await self.browser.new_page()
        await self.page.route("**/*", lambda route: route.fulfill(body=FIXTURE, content_type="text/html"))
        await self.page.goto("https://example.test/")
        self.data = await extract_page_data(self.page)

    async def asyncTearDown(self):
        await self.browser.close()
        await self.playwright.stop()

    async def test_content_is_structured_and_excludes_chrome(self):
        text = [item["text"] for item in self.data["content_blocks"]]
        self.assertIn("Editorial heading", text)
        self.assertIn("Useful editorial copy.", text)
        self.assertIn("First point", text)
        self.assertNotIn("Navigation", text)
        self.assertNotIn("Footer noise", text)
        self.assertNotIn("Talk to an expert", text)
        self.assertTrue(self.data["content_blocks"][0]["source"]["dom_path"])

    async def test_links_keep_scope_and_distinct_cta_occurrences(self):
        links = self.data["links"]
        ctas = [item for item in links if item["text"] == "Talk to an expert"]
        self.assertEqual(2, len(ctas))
        self.assertEqual(2, len({item["interaction_key"] for item in ctas}))
        self.assertEqual("internal", ctas[0]["scope"])
        self.assertEqual("external", next(x for x in links if x["text"] == "External resource")["scope"])
        self.assertTrue(all(item["page_url"] and item["section"] for item in links))

    async def test_faq_and_form_evidence(self):
        faq = next(x for x in self.data["buttons"] if x["text"] == "What is covered?")
        self.assertEqual("faq_accordion", faq["semantic_category"])
        form = self.data["forms"][0]
        self.assertEqual("recaptcha", form["integrations"][0]["provider"])
        self.assertNotIn("g-recaptcha-response", [x["name"] for x in form["fields"]])
        fields = {field["name"]: field for field in form["fields"]}
        self.assertTrue(fields["email"]["visually_marked_required"])
        self.assertFalse(fields["email"]["html_required"])
        self.assertTrue(fields["native"]["html_required"])
        self.assertEqual(["", "qa"], [x["value"] for x in fields["role"]["options"]])
        self.assertEqual(".pdf,.docx", fields["cv"]["file_restrictions"]["accept"])
        self.assertTrue(fields["cv"]["file_restrictions"]["multiple"])


class UrlScopeTests(unittest.TestCase):
    def test_origin_scope_does_not_accept_a_different_port(self):
        self.assertTrue(is_internal_link("https://example.test", "https://example.test/path"))
        self.assertFalse(is_internal_link("https://example.test", "https://example.test:8443/path"))

