"""Render the review and check its evidence browser interactions."""
from pathlib import Path
import json
from playwright.sync_api import sync_playwright

root = Path(__file__).resolve().parents[1]
out = root / 'design' / 'functional-review'
checks, errors = {}, []
with sync_playwright() as p:
    browser = p.chromium.launch(executable_path=r'C:\Program Files\Google\Chrome\Application\chrome.exe', headless=True)
    page = browser.new_page(viewport={'width': 1440, 'height': 1100}, device_scale_factor=1)
    page.set_default_timeout(10000)
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.goto((root / 'review.html').as_uri(), wait_until='load')
    page.screenshot(path=str(out / 'review-desktop.png'), full_page=True)
    page.screenshot(path=str(out / 'review-desktop-top.png'))
    checks['title'] = page.title()
    checks['all_findings'] = page.locator('article.finding:visible').count()
    page.locator('[data-filter="blocker"]').click()
    checks['blockers'] = page.locator('article.finding:visible').count()
    page.locator('[data-filter="confirm"]').click()
    checks['confirmations'] = page.locator('article.finding:visible').count()
    page.locator('[data-filter="all"]').click()
    page.locator('#drc-evidence summary').click()
    page.locator('#drc-search').fill('POWER')
    checks['power_rows'] = page.locator('#drc-body tr:visible').count()
    page.locator('#drc-search').fill('BAT')
    checks['battery_rows'] = page.locator('#drc-body tr:visible').count()
    page.locator('#drc-search').fill('')
    checks['all_drc_rows'] = page.locator('#drc-body tr:visible').count()
    page.locator('#drc-evidence summary').click()
    checks['images'] = page.locator('img').evaluate_all('(items)=>items.every(i=>i.complete&&i.naturalWidth>0)')
    checks['anchors'] = page.locator('a[href^="#"]').evaluate_all('(items)=>items.every(a=>document.querySelector(a.getAttribute("href")))')
    local_links = 0
    for href in page.locator('a').evaluate_all('(items)=>items.map(a=>a.getAttribute("href"))'):
        if href and not href.startswith(('https:', '#', 'data:')):
            assert (root / href.split('#')[0]).is_file(), href
            local_links += 1
    checks['local_links_valid'] = local_links
    checks['desktop_overflow'] = page.evaluate('document.documentElement.scrollWidth>innerWidth')
    page.set_viewport_size({'width': 390, 'height': 844})
    page.evaluate('window.scrollTo(0,0)')
    page.screenshot(path=str(out / 'review-mobile.png'), full_page=True)
    page.screenshot(path=str(out / 'review-mobile-top.png'))
    checks['mobile_overflow'] = page.evaluate('document.documentElement.scrollWidth>innerWidth')
    checks['errors'] = errors
    assert checks['all_findings'] == 9 and checks['blockers'] == 3 and checks['confirmations'] == 6
    assert checks['power_rows'] == 24 and checks['battery_rows'] == 2 and checks['all_drc_rows'] == 62
    assert checks['images'] and checks['anchors'] and not checks['desktop_overflow'] and not checks['mobile_overflow'] and not errors
    browser.close()
(out / 'html-qa.json').write_text(json.dumps(checks, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps(checks, ensure_ascii=True, indent=2))
