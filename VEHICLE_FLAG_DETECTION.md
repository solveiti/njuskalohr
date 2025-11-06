# Enhanced Vehicle Flag Detection

## Overview

The vehicle counting system has been enhanced to specifically target the correct HTML structure for detecting "Novo vozilo" (New Vehicle) and "Rabljeno vozilo" (Used Vehicle) flags on njuskalo.hr.

## 🔍 HTML Structure Analysis

Based on the website inspection, vehicle flags are located in:

```html
<li class="entity-flag">
  <span class="flag">Novo vozilo</span>
</li>
```

## 🛠️ Implementation Details

### Enhanced Detection Method

The new `detect_vehicle_flags()` method implements a three-tier detection strategy:

#### 1. Primary Detection (Most Accurate)

```python
flag_elements = self.driver.find_elements(By.CSS_SELECTOR, "li.entity-flag span.flag")
```

- Targets the exact structure: `li.entity-flag` containing `span.flag`
- Reads text directly from the span element
- Most reliable method for accurate counting

#### 2. Secondary Detection (Container-based)

```python
flag_containers = self.driver.find_elements(By.CSS_SELECTOR, "li.entity-flag")
```

- Searches broader `li.entity-flag` containers
- Fallback when spans are not found directly
- Still maintains specificity to flag elements

#### 3. Fallback Detection (General)

```python
ad_selectors = ['.entity-item', '.ad-item', '.listing-item', ...]
```

- Traditional text search within ad elements
- Used only when specific flag elements are not found
- Maintains backward compatibility

### Key Improvements

1. **Precision**: Directly targets the vehicle flag elements instead of searching general ad content
2. **Reliability**: Multi-tier approach ensures detection even if page structure varies
3. **Performance**: More efficient by targeting specific elements first
4. **Debugging**: Enhanced logging to track detection success at each level

## 📊 Usage Example

```python
from njuskalo_sitemap_scraper import NjuskaloSitemapScraper

scraper = NjuskaloSitemapScraper(headless=True)
scraper.setup_browser()

# Navigate to a store page
scraper.driver.get("https://www.njuskalo.hr/trgovina/some_store?categoryId=2")

# Detect vehicle flags on current page
vehicle_counts = scraper.detect_vehicle_flags()
print(f"New vehicles: {vehicle_counts['new_count']}")
print(f"Used vehicles: {vehicle_counts['used_count']}")

# Full pagination-based counting
full_counts = scraper.count_vehicle_ads("https://www.njuskalo.hr/trgovina/some_store")
```

## 🔧 Testing

Run the vehicle detection test to verify functionality:

```bash
python test_vehicle_detection.py
```

The test will:

- Validate CSS selectors
- Test detection on a real store page
- Compare single-page vs. paginated results
- Show sample flag text found

## 🎯 Benefits

1. **Accuracy**: More precise counting by targeting actual flag elements
2. **Robustness**: Multiple detection strategies handle various page layouts
3. **Maintainability**: Clear separation of detection logic in dedicated method
4. **Debugging**: Enhanced logging for troubleshooting detection issues

## 📝 Technical Notes

- The method returns a dictionary with `'new_count'` and `'used_count'` keys
- Debug logging shows the number of flag elements found
- Graceful error handling ensures the scraper continues even if detection fails
- Compatible with existing database schema and Excel export functionality

---

_This enhancement significantly improves the accuracy of vehicle counting for auto moto stores on njuskalo.hr._
