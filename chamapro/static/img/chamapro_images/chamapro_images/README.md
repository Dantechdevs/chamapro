# ChamaPro Brand Images

All images generated to match ChamaPro's exact color palette:
- Brand green:  #0d6e4f
- Accent:       #00c97a
- Sidebar dark: #071f17
- Amber accent: #f59e0b

## Files & Usage

| File | Size | Use in template |
|------|------|-----------------|
| hero_banner.png | 1200×500 | Landing page hero, dashboard top banner |
| auth_background.png | 800×600 | Login / register page background |
| empty_state.png | 600×400 | Empty tables / first-time dashboard |
| feature_contributions.png | 400×280 | Contributions feature card |
| feature_loans.png | 400×280 | Loans feature card |
| feature_investments.png | 400×280 | Investments feature card |
| member_avatars.png | 400×200 | Member list placeholder / onboarding |
| logo_placeholder.png | 400×100 | Until you supply a real logo PNG |
| bg_pattern.png | 200×200 | Tileable sidebar / section background |
| mpesa_illustration.png | 500×300 | M-Pesa / transactions section |
| reports_chart.png | 500×300 | Reports section header |
| og_image.png | 1200×630 | Open Graph meta image for social sharing |

## Django static setup

1. Copy the `chamapro_images/` folder to `static/img/`
2. Reference in templates:
   ```html
   {% load static %}
   <img src="{% static 'img/hero_banner.png' %}" alt="ChamaPro">
   ```

## base.html color variables (already correct)

```css
:root {
  --brand:       #0d6e4f;
  --brand-light: #1a8f68;
  --brand-xlight:#e6f5f0;
  --brand-dark:  #064d38;
  --sidebar-bg:  #071f17;
  --accent:      #00c97a;
  --accent2:     #f59e0b;
}
```
Your base.html CSS already matches perfectly — no changes needed to variables.
