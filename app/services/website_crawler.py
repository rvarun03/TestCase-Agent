from urllib.parse import urljoin, urlsplit, urldefrag
import asyncio
import ipaddress
import json
import socket
from playwright.async_api import async_playwright
from collections import deque

def _port(parts) -> int:
    return parts.port or (443 if parts.scheme == "https" else 80)

def normalize_url(url: str) -> str:
    """Remove fragments and query parameters for basic page discovery."""
    return urlsplit(urldefrag(url).url)._replace(query="").geturl()

def is_internal_link(base_url: str, link_url: str) -> bool:
    """Check that an HTTP(S) link is in the approved origin scope."""
    base, link = urlsplit(base_url), urlsplit(link_url)
    return (link.scheme in ("http", "https") and link.hostname is not None
            and link.hostname.lower() == base.hostname.lower() and _port(link) == _port(base))

def is_safe_public_url(url: str) -> bool:
    """Reject credentials, localhost, and private/reserved targets before navigation."""
    parts = urlsplit(url)
    if parts.scheme not in ("http", "https") or not parts.hostname or parts.username:
        return False
    try:
        addresses = {item[4][0] for item in socket.getaddrinfo(parts.hostname, None)}
        return bool(addresses) and all(not (
            ipaddress.ip_address(address).is_private or ipaddress.ip_address(address).is_loopback
            or ipaddress.ip_address(address).is_link_local or ipaddress.ip_address(address).is_reserved
            or ipaddress.ip_address(address).is_unspecified or ipaddress.ip_address(address).is_multicast
        ) for address in addresses)
    except (OSError, ValueError):
        return False

async def extract_page_data(page) -> dict:
    """Extract visible editorial blocks and actionable elements with DOM evidence."""
    data = await page.evaluate(r"""() => {
        const clean = value => (value || "").replace(/\s+/g, " ").trim();
        const attrs = el => Object.fromEntries(Array.from(el.attributes)
          .filter(a => ["id","class","name","type","role","href","for","action","method","placeholder","accept","aria-label","aria-labelledby","aria-expanded","aria-required","target","rel","autocomplete","multiple"].includes(a.name)).map(a => [a.name,a.value]));
        const visible = el => { const s = getComputedStyle(el); return el.getClientRects().length > 0 && s.display !== "none" && s.visibility !== "hidden" && el.getAttribute("aria-hidden") !== "true"; };
        const path = el => { const p=[]; for(let n=el;n&&n.nodeType===1&&n!==document.body;n=n.parentElement){const siblings=Array.from(n.parentElement?n.parentElement.children:[]).filter(x=>x.tagName===n.tagName);p.unshift(`${n.tagName.toLowerCase()}:nth-of-type(${siblings.indexOf(n)+1})`)} return "body > "+p.join(" > "); };
        const section = el => { const c=el.closest("section,article,main,form,[role=region]"); const h=c&&c.querySelector("h1,h2,h3,h4,h5,h6"); return {landmark:c?(c.tagName.toLowerCase()+(c.id?`#${c.id}`:"")):"body",heading:clean(h&&h.innerText)||null,dom_path:path(c||el)}; };
        const name = el => clean(el.getAttribute("aria-label")||el.getAttribute("title")||el.innerText||el.value);
        const key = (el,target="") => `${el.tagName.toLowerCase()}|${target}|${path(el)}`;
        const ignoredContent = el => el.closest("nav,footer,header,aside,form,[role=navigation],[role=contentinfo],button,a,input,select,textarea,script,style,template,[hidden],[aria-hidden=true]");
        const uniqueVisible = selector => Array.from(document.querySelectorAll(selector)).filter(visible).filter((el,i,a)=>a.indexOf(el)===i);

        const content_blocks = uniqueVisible("h1,h2,h3,h4,h5,h6,p,li,blockquote").filter(el=>!ignoredContent(el)).filter(el=>!el.closest("li")||el.parentElement.matches("ul,ol")).map(el=>({
          type:/^h[1-6]$/.test(el.tagName.toLowerCase())?"heading":el.tagName.toLowerCase()==="li"?"list_item":el.tagName.toLowerCase()==="blockquote"?"quote":"paragraph",
          level:/^h[1-6]$/.test(el.tagName.toLowerCase())?Number(el.tagName[1]):null,text:clean(el.innerText),list_type:el.tagName.toLowerCase()==="li"?el.parentElement.tagName.toLowerCase():null,
          source:{tag:el.tagName.toLowerCase(),attributes:attrs(el),dom_path:path(el),section:section(el)}})).filter(block=>block.text);

        const links = uniqueVisible("a[href]").map(el=>{ const href=el.href, inNav=!!el.closest("nav,[role=navigation]"),inFooter=!!el.closest("footer,[role=contentinfo]"); const cta=!!el.closest("[class*=cta i],[class*=button i],[class*=hero i]")||/^(talk|contact|get started|learn more|read|see )/i.test(name(el)); const target=new URL(href); return {interaction_key:key(el,href),page_url:location.href,tag:"a",semantic_category:inNav?"navigation_link":inFooter?"footer_link":cta?"cta_link":"content_link",text:name(el),href,scope:target.hostname===location.hostname&&target.port===location.port?"internal":"external",target:el.getAttribute("target"),attributes:attrs(el),section:section(el),dom_path:path(el)}; });

        const buttons = uniqueVisible('button,[role="button"],input[type="button"],input[type="submit"],input[type="reset"]').map(el=>{ const tag=el.tagName.toLowerCase(),type=(el.getAttribute("type")||"").toLowerCase()||null,context=(el.closest("[class]")?.className||"").toString().toLowerCase(),insideForm=!!el.closest("form"),expanded=el.getAttribute("aria-expanded"); const category=(type==="submit"||(tag==="button"&&insideForm&&!type))?"form_submit":(expanded!==null&&/faq|accordion/.test(context))?"faq_accordion":expanded!==null?"expandable_control":/carousel|slider|swiper|slick/.test(context)?"carousel_navigation":el.closest("nav")?"navigation_control":"action_button"; return {interaction_key:key(el),page_url:location.href,tag,semantic_category:category,text:name(el),type,aria_expanded:expanded,disabled:el.matches(":disabled"),attributes:attrs(el),section:section(el),dom_path:path(el)}; });

        const labelFor = el => { const id=el.id,labelled=(el.getAttribute("aria-labelledby")||"").split(/\s+/).map(i=>document.getElementById(i)).filter(Boolean).map(x=>clean(x.innerText)).join(" "),explicit=el.labels?Array.from(el.labels).map(x=>clean(x.innerText)).filter(Boolean).join(" "):"",wrapping=el.closest("label"),ancestor=el.closest(".field,.form-group,.form-field,[role=group],div"),nearby=ancestor?Array.from(ancestor.querySelectorAll("label,legend,.label")).map(x=>clean(x.innerText)).filter(Boolean).join(" "):""; return clean(el.getAttribute("aria-label")||labelled||explicit||(wrapping&&wrapping.innerText)||nearby||(id&&document.querySelector(`label[for="${CSS.escape(id)}"]`)?.innerText)); };
        const captcha = el => /recaptcha|g-recaptcha|hcaptcha|cf-turnstile/i.test(`${el.name} ${el.id} ${el.className} ${el.getAttribute("data-sitekey")||""}`);
        const field = el => { const label=labelFor(el),tag=el.tagName.toLowerCase(),type=(el.getAttribute("type")||"").toLowerCase()||null; return {interaction_key:key(el,el.name||el.id||type||tag),page_url:location.href,tag,semantic_category:"form_field",type,name:el.getAttribute("name"),id:el.id||null,label,placeholder:el.getAttribute("placeholder"),html_required:el.required===true,visually_marked_required:/(^|\s)\*(\s|$)/.test(label)||el.getAttribute("aria-required")==="true",disabled:el.disabled===true,options:tag==="select"?Array.from(el.options).map(o=>({text:clean(o.text),value:o.value,disabled:o.disabled})):[],file_restrictions:type==="file"?{accept:el.getAttribute("accept"),multiple:el.multiple,max_size:el.getAttribute("data-max-size")||null}:null,attributes:attrs(el),section:section(el),dom_path:path(el)}; };
        const fields=uniqueVisible("input,textarea,select").filter(el=>!captcha(el)&&el.type!=="hidden");
        const forms=Array.from(document.querySelectorAll("form")).map((form,index)=>({form_id:form.id||`form_${index+1}`,action:form.action,method:form.method,fields:fields.filter(el=>el.closest("form")===form).map(field),integrations:Array.from(form.querySelectorAll("input,textarea,select,[data-sitekey]")).filter(captcha).map(el=>({provider:/hcaptcha/i.test(el.outerHTML)?"hcaptcha":/turnstile/i.test(el.outerHTML)?"turnstile":"recaptcha",tag:el.tagName.toLowerCase(),attributes:attrs(el)}))}));
        return {content_blocks,links,buttons,forms,standalone_fields:fields.filter(el=>!el.closest("form")).map(field)};
    }""")
    # Compatibility alias; new consumers should use links.
    return {"url": page.url, "title": await page.title(), **data, "navigation_links": data["links"]}

async def crawl_website(website_url: str, max_pages: int = 10) -> list[dict]:
    if not is_safe_public_url(website_url):
        raise ValueError("Provide a valid public HTTP or HTTPS URL")
    website_url = normalize_url(website_url)
    queue, visited, pages_data = deque([website_url]), set(), []
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        try:
            while queue and len(visited) < max_pages:
                current_url = queue.popleft()
                if current_url in visited or not is_internal_link(website_url,current_url): continue
                visited.add(current_url); page = await browser.new_page()
                try:
                    response = await page.goto(current_url,wait_until="domcontentloaded",timeout=15000)
                    if not is_internal_link(website_url,page.url) or not is_safe_public_url(page.url): print("SKIPPED REDIRECT:",page.url); continue
                    if response is None or response.status>=400: print("PAGE UNAVAILABLE:",current_url); continue
                    await page.wait_for_timeout(700); page_data=await extract_page_data(page); pages_data.append(page_data)
                    print("\nVISITING:",page_data["url"]); print("TITLE:",page_data["title"]); print("BUTTONS:",len(page_data["buttons"])); print("LINKS:",len(page_data["links"])); print("FORMS:",len(page_data["forms"]))
                    for link in page_data["links"]:
                        if link["scope"] != "internal": continue
                        full_url=normalize_url(urljoin(page.url,link["href"]))
                        if is_internal_link(website_url,full_url) and full_url not in visited and full_url not in queue: queue.append(full_url)
                    print("PAGES WAITING:",len(queue))
                except Exception as error: print("ERROR:",current_url,error)
                finally: await page.close()
        finally: await browser.close()
    return pages_data