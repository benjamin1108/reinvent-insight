# Design Document

## Overview

本设计文档详细说明如何将Library View和Summary Card组件从功能性实现提升到顶尖产品级别的用户体验。设计遵循现代UI/UX最佳实践，包括信息架构优化、视觉降噪、可访问性增强和细节打磨。

核心设计原则：
- **信息层级清晰**：通过视觉权重和间距建立明确的信息优先级
- **视觉降噪**：移除冗余元素，让用户专注于核心内容
- **可访问性优先**：确保所有用户都能轻松阅读和使用界面
- **细节打磨**：关注每个像素，追求完美的视觉呈现

## Architecture

### Component Structure

```
LibraryView (Container)
├── Section Header
│   ├── Title Group
│   │   ├── Section Indicator
│   │   ├── Section Title
│   │   └── Article Count Badge
│   └── Filter Controls
│       ├── Level Filter (CustomDropdown)
│       ├── Year Filter (CustomDropdown)
│       └── Sort Button
├── Card Grid
│   └── SummaryCard (Multiple)
│       ├── Content Area
│       │   ├── Title Container
│       │   └── Subtitle Area
│       └── Metadata Footer
│           ├── Left Group (Content Type, Word Count)
│           └── Right Group (Category Badge, Year Badge, Level Badge)
└── Custom Scrollbar
```

### Design Layers

1. **Layout Layer**: 负责组件布局、间距和响应式行为
2. **Visual Layer**: 负责颜色、对比度、阴影和视觉效果
3. **Interaction Layer**: 负责hover状态、过渡动画和用户反馈
4. **Accessibility Layer**: 负责对比度、焦点管理和屏幕阅读器支持

## Components and Interfaces

### 1. SummaryCard Component

#### Props Interface
```typescript
interface SummaryCardProps {
  summaryType: 'reinvent' | 'other';
  titleEn: string;
  titleCn: string;
  wordCount: number;
  year?: string;
  level?: string;
  hash: string;
  contentType: 'pdf' | 'youtube' | 'other';
  isPdf: boolean;
}
```

#### Visual Refinements

**Metadata Area Cleanup:**
- Remove redundant "RE:INVENT" badge when already in re:Invent section
- Consolidate badges to show only: Category (精选/re:Invent), Year, Level
- Use consistent low-saturation backgrounds for all badges
- Reduce visual weight of word count and document icon

**Badge Styling:**
```css
/* Unified badge style with low saturation */
.summary-card__badge {
  background: rgba(100, 116, 139, 0.15);  /* Low saturation gray */
  color: #94a3b8;  /* Muted text color */
  border: 1px solid rgba(100, 116, 139, 0.2);
  padding: 4px 10px;
  border-radius: 6px;
  font-size: 0.625rem;
  font-weight: 600;
  letter-spacing: 0.05em;
  text-transform: uppercase;
}

/* Category badge - slightly more prominent */
.summary-card__badge--category {
  background: rgba(34, 211, 238, 0.12);
  color: #22d3ee;
  border-color: rgba(34, 211, 238, 0.25);
}

/* Level badge for re:Invent */
.summary-card__badge--level {
  background: rgba(251, 146, 60, 0.12);
  color: #fb923c;
  border-color: rgba(251, 146, 60, 0.25);
}
```

### 2. Contrast and Readability

#### Color Palette Adjustments

**Text Colors (WCAG AA Compliant):**
```css
/* Card description text - improved contrast */
.summary-card__subtitle {
  color: #94a3b8;  /* Lightened from #64748b */
  opacity: 1;      /* Remove opacity, bake it into color */
}

/* Blue badge background - increased luminance */
.library-view__article-count {
  background: rgba(34, 211, 238, 0.18);  /* Increased from 0.1 */
  color: #22d3ee;
  border: 1px solid rgba(34, 211, 238, 0.3);
}
```

#### Contrast Ratios
- Normal text (14px): Minimum 4.5:1 contrast ratio
- Large text (18px+): Minimum 3:1 contrast ratio
- UI components: Minimum 3:1 contrast ratio
- Target: Exceed WCAG AA standards, approach AAA where possible

### 3. Spacing and Layout

#### Card Internal Spacing
```css
.summary-card {
  padding: 1.75rem;  /* Increased from 1.5rem */
}

.summary-card__title-container {
  margin-bottom: 1rem;  /* Increased from 0.75rem */
}

.summary-card__subtitle-area {
  margin-bottom: 1rem;  /* Increased from 0.5rem */
}

.summary-card__metadata {
  padding-top: 1rem;  /* Increased from 0.75rem */
  margin-top: auto;   /* Push to bottom */
}
```

#### Metadata Element Spacing
```css
.summary-card__metadata-left {
  gap: 1rem;  /* Increased from 0.75rem */
}

.summary-card__metadata-right {
  gap: 0.625rem;  /* Increased from 0.5rem */
}
```

### 4. Custom Scrollbar

#### Implementation
```css
/* Webkit browsers (Chrome, Safari, Edge) */
::-webkit-scrollbar {
  width: 10px;
  height: 10px;
}

::-webkit-scrollbar-track {
  background: rgba(15, 23, 42, 0.3);
  border-radius: 5px;
}

::-webkit-scrollbar-thumb {
  background: rgba(71, 85, 105, 0.5);
  border-radius: 5px;
  transition: background 0.2s ease;
}

::-webkit-scrollbar-thumb:hover {
  background: rgba(71, 85, 105, 0.7);
}

/* Firefox */
* {
  scrollbar-width: thin;
  scrollbar-color: rgba(71, 85, 105, 0.5) rgba(15, 23, 42, 0.3);
}
```

### 5. Filter Controls Refinement

#### Filled Style Dropdowns
```css
.custom-dropdown-trigger {
  /* Replace outlined style with filled style */
  background: rgba(51, 65, 85, 0.4);  /* Subtle filled background */
  border: 1px solid transparent;       /* Remove visible border */
  backdrop-filter: blur(8px);
  transition: all 0.2s ease;
}

.custom-dropdown-trigger:hover {
  background: rgba(51, 65, 85, 0.6);
  border-color: rgba(100, 116, 139, 0.3);
}

.custom-dropdown-trigger:focus {
  background: rgba(51, 65, 85, 0.7);
  border-color: rgba(34, 211, 238, 0.4);
  outline: none;
}
```

#### Alignment Fixes
```css
.library-view__section-header {
  display: flex;
  align-items: center;  /* Ensure vertical centering */
  gap: 1rem;
  min-height: 3rem;     /* Consistent height */
}

.library-view__section-title {
  line-height: 1.2;     /* Tight line height */
  margin: 0;            /* Remove default margins */
}

.library-view__filters {
  display: flex;
  align-items: center;  /* Vertical center */
  gap: 0.75rem;
}
```

### 6. Logout Button Redesign

#### Ghost Button Style
```css
.app-header__logout-button {
  /* Remove red danger styling */
  background: transparent;
  border: 1px solid transparent;
  color: #94a3b8;
  padding: 0.5rem 1rem;
  transition: all 0.2s ease;
}

.app-header__logout-button:hover {
  background: rgba(100, 116, 139, 0.1);
  border-color: rgba(100, 116, 139, 0.3);
  color: #cbd5e1;
}

.app-header__logout-button:active {
  background: rgba(100, 116, 139, 0.2);
}
```

### 7. Smart Title Truncation

#### Title Processing Logic
```javascript
function processCardTitle(title, summaryType, currentFilter) {
  // Remove redundant prefix when in filtered view
  if (summaryType === 'reinvent' && currentFilter === 'reinvent') {
    // Remove "AWS re:Invent YYYY -" prefix
    title = title.replace(/^AWS re:Invent \d{4}\s*-\s*/i, '');
  }
  
  return title.trim();
}
```

#### Implementation in Component
```javascript
const displayTitle = computed(() => {
  return processCardTitle(
    props.titleEn,
    props.summaryType,
    currentSectionFilter.value
  );
});
```

## Data Models

### Theme Configuration
```typescript
interface ThemeColors {
  // Background colors
  background: {
    primary: string;      // Main page background
    card: string;         // Card background
    elevated: string;     // Elevated elements
  };
  
  // Text colors (WCAG compliant)
  text: {
    primary: string;      // Main text (contrast >= 7:1)
    secondary: string;    // Secondary text (contrast >= 4.5:1)
    tertiary: string;     // Tertiary text (contrast >= 4.5:1)
    muted: string;        // Muted text (contrast >= 4.5:1)
  };
  
  // Accent colors
  accent: {
    primary: string;      // Primary accent (cyan)
    secondary: string;    // Secondary accent (orange)
    success: string;      // Success state
    warning: string;      // Warning state
    error: string;        // Error state (use sparingly)
  };
  
  // UI element colors
  ui: {
    border: string;       // Border color
    divider: string;      // Divider lines
    hover: string;        // Hover backgrounds
    active: string;       // Active state
    disabled: string;     // Disabled state
  };
}
```

### Spacing Scale
```typescript
interface SpacingScale {
  xs: string;    // 0.25rem (4px)
  sm: string;    // 0.5rem (8px)
  md: string;    // 0.75rem (12px)
  lg: string;    // 1rem (16px)
  xl: string;    // 1.5rem (24px)
  '2xl': string; // 2rem (32px)
  '3xl': string; // 3rem (48px)
}
```

## Data Models

### Accessibility Configuration
```typescript
interface AccessibilityConfig {
  contrastMode: 'normal' | 'high';
  reducedMotion: boolean;
  fontSize: 'small' | 'medium' | 'large';
  focusIndicators: boolean;
}
```



## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system-essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Visual Consistency Properties

**Property 1: Redundant tag removal**
*For any* Summary Card rendered in a re:Invent section context, the metadata area should not contain a duplicate "RE:INVENT" badge
**Validates: Requirements 1.1**

**Property 2: Badge saturation consistency**
*For any* collection of metadata badges rendered on a card, all badge background colors should have HSL saturation values within a consistent range (variance < 15%)
**Validates: Requirements 1.2**

**Property 3: Visual hierarchy in metadata**
*For any* Summary Card, the word count and document icon elements should have lower opacity or lighter color values than primary metadata badges
**Validates: Requirements 1.3**

**Property 4: Low-saturation badge backgrounds**
*For any* year or level badge, the background color HSL saturation value should be less than 30%
**Validates: Requirements 1.4**

**Property 5: Metadata spacing consistency**
*For any* Summary Card metadata area, the gap between adjacent elements should be at least 0.5rem
**Validates: Requirements 1.5**

### Accessibility Properties

**Property 6: Text contrast compliance**
*For any* card description text element, the contrast ratio between text color and background color should be at least 4.5:1
**Validates: Requirements 2.1, 2.3**

**Property 7: Badge luminance distinction**
*For any* blue badge element, the relative luminance difference from the page background should be at least 0.3
**Validates: Requirements 2.2**

**Property 8: UI element contrast**
*For any* colored UI element (buttons, badges, controls), the contrast ratio with its background should be at least 3:1
**Validates: Requirements 2.4**

### Spacing Properties

**Property 9: Card padding minimum**
*For any* Summary Card, the computed padding on all four sides should be at least 1.5rem (24px)
**Validates: Requirements 3.1**

**Property 10: Title prefix removal**
*For any* card title in a re:Invent filtered view, the displayed title should not start with "AWS re:Invent" followed by a year
**Validates: Requirements 3.2, 7.1, 7.2**

**Property 11: Internal spacing adequacy**
*For any* Summary Card, the margin-bottom of title container should be at least 0.75rem, and subtitle area margin-bottom should be at least 0.5rem
**Validates: Requirements 3.3**

**Property 12: Metadata bottom spacing**
*For any* Summary Card, the padding-top of the metadata area should be at least 0.75rem
**Validates: Requirements 3.4**

### Scrollbar Properties

**Property 13: Scrollbar color darkness**
*For any* custom scrollbar element (track or thumb), the color luminance value should be less than 0.3 (dark)
**Validates: Requirements 4.2**

**Property 14: Scrollbar transparency**
*For any* scrollbar track background, the alpha channel value should be between 0.1 and 0.5 (semi-transparent)
**Validates: Requirements 4.3**

**Property 15: Scrollbar thumb contrast**
*For any* scrollbar, the thumb luminance should be greater than track luminance, and both should have defined transition properties
**Validates: Requirements 4.4**

**Property 16: Scrollbar hover subtlety**
*For any* scrollbar thumb hover state, the luminance change from default state should be less than 0.2 (20%)
**Validates: Requirements 4.5**

### Filter Control Properties

**Property 17: Filter vertical alignment**
*For any* filter bar, all child elements should have align-items: center applied and share the same vertical center point
**Validates: Requirements 5.1**

**Property 18: Dropdown filled style**
*For any* dropdown trigger element, the background should not be transparent and border should be transparent or have opacity < 0.3
**Validates: Requirements 5.2**

**Property 19: Filter visual weight consistency**
*For any* collection of filter controls, the font-weight and font-size values should be identical across all controls
**Validates: Requirements 5.3**

**Property 20: Filter baseline alignment**
*For any* filter bar, the section title and filter controls should have consistent line-height values for proper baseline alignment
**Validates: Requirements 5.4**

**Property 21: Filter spacing consistency**
*For any* filter bar, the gap between filter elements should be consistent (variance < 0.25rem)
**Validates: Requirements 5.5**

### Button Styling Properties

**Property 22: Logout button neutrality**
*For any* logout button, the default state color HSL hue should not be in the red range (0-30° or 330-360°)
**Validates: Requirements 6.1**

**Property 23: Logout hover neutrality**
*For any* logout button hover state, the color HSL hue should not be in the red range (0-30° or 330-360°)
**Validates: Requirements 6.2**

**Property 24: Logout visual de-emphasis**
*For any* logout button, the opacity or background alpha should be lower than primary action buttons
**Validates: Requirements 6.3**

**Property 25: Logout default subtlety**
*For any* logout button in default state, the text opacity or background alpha should be less than 0.7
**Validates: Requirements 6.4**

**Property 26: Logout interaction neutrality**
*For any* logout button state (default, hover, active), the color HSL hue should remain outside the red/orange range (0-60° or 330-360°)
**Validates: Requirements 6.5**

### Title Processing Properties

**Property 27: Title variation in collections**
*For any* collection of 3 or more cards in the same section, at least 70% of cards should have different first 10 characters in their titles
**Validates: Requirements 7.4**

**Property 28: Title tooltip preservation**
*For any* card title element, the title attribute should contain the full unprocessed original title text
**Validates: Requirements 7.5**

### Code Quality Properties

**Property 29: BEM naming consistency**
*For any* CSS class name in component stylesheets, the name should match BEM pattern (block__element--modifier)
**Validates: Requirements 8.1**

**Property 30: CSS custom property usage**
*For any* theme-related color value in component styles, the value should reference a CSS custom property (var(--*))
**Validates: Requirements 8.2**

**Property 31: Transition definition**
*For any* element with hover state styling, a CSS transition property should be defined
**Validates: Requirements 8.3**

**Property 32: Responsive spacing scale**
*For any* spacing value defined in media queries, the value should be a multiple of the base spacing unit (0.25rem)
**Validates: Requirements 8.4**

**Property 33: Accessibility attribute presence**
*For any* interactive element (buttons, dropdowns, links), appropriate ARIA labels or roles should be present
**Validates: Requirements 8.5**

## Error Handling

### Visual Rendering Errors

**Missing Content Handling:**
- If card title is empty, display placeholder text "Untitled"
- If word count is 0 or undefined, display "—" instead of "0字"
- If year is missing, omit year badge entirely rather than showing empty badge

**Color Calculation Errors:**
- If contrast ratio calculation fails, fall back to predefined safe color pairs
- If HSL conversion fails, use RGB fallback values
- Log warnings for any color values that don't meet accessibility standards

**Layout Errors:**
- If computed padding is less than minimum, force minimum padding via !important
- If element alignment fails, fall back to flex-start alignment
- Monitor and log any layout shift (CLS) issues

### Interaction Errors

**Scrollbar Rendering:**
- If custom scrollbar styles fail to apply, ensure native scrollbar remains functional
- Detect browser support for custom scrollbar properties before applying
- Provide fallback for browsers that don't support ::-webkit-scrollbar

**Filter Control Errors:**
- If dropdown fails to open, log error and maintain current filter state
- If filter value is invalid, reset to "all" option
- Ensure filter controls remain keyboard accessible even if JavaScript fails

**Title Processing Errors:**
- If regex matching fails, display original title without modification
- If title is too long for container, apply CSS ellipsis truncation
- Preserve full title in tooltip even if processing fails

## Testing Strategy

### Unit Testing

**Component Rendering Tests:**
- Test SummaryCard renders correctly with all prop combinations
- Test metadata area renders correct badges based on summaryType
- Test title processing logic removes prefixes correctly
- Test spacing calculations return correct rem values

**Color Utility Tests:**
- Test contrast ratio calculation function with known color pairs
- Test HSL conversion and saturation extraction
- Test luminance calculation for various color values
- Test color validation against WCAG standards

**CSS Class Tests:**
- Test BEM naming validator correctly identifies valid/invalid class names
- Test CSS custom property extractor finds all theme variables
- Test transition property detector identifies missing transitions

### Property-Based Testing

We will use **fast-check** (JavaScript property-based testing library) for implementing property-based tests.

**Configuration:**
- Minimum 100 iterations per property test
- Use appropriate generators for colors, spacing values, and DOM structures
- Seed random generation for reproducible test failures

**Test Generators:**
```javascript
// Color generator - produces valid CSS colors
const colorGen = fc.record({
  r: fc.integer({ min: 0, max: 255 }),
  g: fc.integer({ min: 0, max: 255 }),
  b: fc.integer({ min: 0, max: 255 }),
  a: fc.double({ min: 0, max: 1 })
});

// Spacing generator - produces valid rem values
const spacingGen = fc.double({ min: 0, max: 5 })
  .map(n => `${(Math.round(n * 4) / 4).toFixed(2)}rem`);

// Card data generator
const cardDataGen = fc.record({
  titleEn: fc.string({ minLength: 10, maxLength: 100 }),
  titleCn: fc.string({ minLength: 10, maxLength: 100 }),
  wordCount: fc.integer({ min: 100, max: 50000 }),
  year: fc.option(fc.integer({ min: 2015, max: 2024 }).map(String)),
  level: fc.option(fc.constantFrom('100', '200', '300', '400', 'Keynote')),
  summaryType: fc.constantFrom('reinvent', 'other')
});
```

**Property Test Examples:**

*Property 6: Text contrast compliance*
```javascript
// Feature: library-view-ux-refinement, Property 6: Text contrast compliance
test('card description text meets WCAG AA contrast', () => {
  fc.assert(
    fc.property(cardDataGen, colorGen, colorGen, (cardData, textColor, bgColor) => {
      const card = renderCard(cardData, { textColor, bgColor });
      const descElement = card.querySelector('.summary-card__subtitle');
      const computedTextColor = getComputedStyle(descElement).color;
      const computedBgColor = getComputedStyle(descElement).backgroundColor;
      const contrastRatio = calculateContrastRatio(computedTextColor, computedBgColor);
      return contrastRatio >= 4.5;
    }),
    { numRuns: 100 }
  );
});
```

*Property 10: Title prefix removal*
```javascript
// Feature: library-view-ux-refinement, Property 10: Title prefix removal
test('re:Invent titles have prefix removed in filtered view', () => {
  fc.assert(
    fc.property(
      fc.string({ minLength: 20 }),
      fc.integer({ min: 2015, max: 2024 }),
      (titleSuffix, year) => {
        const fullTitle = `AWS re:Invent ${year} - ${titleSuffix}`;
        const cardData = { titleEn: fullTitle, summaryType: 'reinvent' };
        const card = renderCard(cardData, { inReinventSection: true });
        const displayedTitle = card.querySelector('.summary-card__title').textContent;
        return !displayedTitle.startsWith('AWS re:Invent');
      }
    ),
    { numRuns: 100 }
  );
});
```

*Property 22: Logout button neutrality*
```javascript
// Feature: library-view-ux-refinement, Property 22: Logout button neutrality
test('logout button does not use red color', () => {
  fc.assert(
    fc.property(fc.constant(null), () => {
      const button = document.querySelector('.app-header__logout-button');
      const computedColor = getComputedStyle(button).color;
      const hsl = rgbToHsl(computedColor);
      // Red hue is 0-30° or 330-360°
      return (hsl.h > 30 && hsl.h < 330);
    }),
    { numRuns: 100 }
  );
});
```

*Property 27: Title variation in collections*
```javascript
// Feature: library-view-ux-refinement, Property 27: Title variation in collections
test('card titles in collection are varied', () => {
  fc.assert(
    fc.property(
      fc.array(cardDataGen, { minLength: 3, maxLength: 10 }),
      (cardDataArray) => {
        const cards = cardDataArray.map(data => renderCard(data, { inReinventSection: true }));
        const titlePrefixes = cards.map(card => 
          card.querySelector('.summary-card__title').textContent.substring(0, 10)
        );
        const uniquePrefixes = new Set(titlePrefixes);
        const variationRatio = uniquePrefixes.size / titlePrefixes.length;
        return variationRatio >= 0.7;
      }
    ),
    { numRuns: 100 }
  );
});
```

### Integration Testing

**Full Page Rendering:**
- Test Library View renders with multiple cards and filters
- Test scrollbar appears and functions correctly
- Test filter interactions update card display
- Test responsive behavior at various breakpoints

**Accessibility Testing:**
- Run automated accessibility audits (axe-core)
- Test keyboard navigation through all interactive elements
- Test screen reader announcements for state changes
- Verify focus indicators are visible and clear

**Visual Regression Testing:**
- Capture screenshots of key states (default, hover, filtered)
- Compare against baseline images
- Flag any unexpected visual changes
- Test across different browsers and screen sizes

### Manual Testing Checklist

- [ ] Verify all text is readable in dark mode
- [ ] Check scrollbar blends with theme
- [ ] Confirm no redundant badges appear
- [ ] Test filter alignment at various zoom levels
- [ ] Verify logout button doesn't look alarming
- [ ] Check card spacing feels comfortable
- [ ] Test with real content of varying lengths
- [ ] Verify tooltips show full titles
- [ ] Check responsive behavior on mobile devices
- [ ] Test with high contrast mode enabled
- [ ] Verify reduced motion preferences are respected
