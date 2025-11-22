# Implementation Plan

- [x] 1. Set up testing infrastructure and utilities
  - Install fast-check library for property-based testing
  - Create color utility functions (contrast ratio, HSL conversion, luminance calculation)
  - Create CSS property extraction utilities for testing
  - Set up test fixtures for card data generation
  - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5_

- [ ]* 1.1 Write property test for color contrast utilities
  - **Property 6: Text contrast compliance**
  - **Validates: Requirements 2.1, 2.3**

- [x] 2. Refactor SummaryCard metadata area
  - Remove redundant "RE:INVENT" badge logic from metadata rendering
  - Consolidate badge display to show only: Category, Year, Level
  - Update badge CSS to use unified low-saturation styling
  - Reduce visual weight of word count and document icon elements
  - Adjust metadata element spacing for better hierarchy
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5_

- [ ]* 2.1 Write property test for redundant tag removal
  - **Property 1: Redundant tag removal**
  - **Validates: Requirements 1.1**

- [ ]* 2.2 Write property test for badge saturation consistency
  - **Property 2: Badge saturation consistency**
  - **Validates: Requirements 1.2**

- [ ]* 2.3 Write property test for visual hierarchy
  - **Property 3: Visual hierarchy in metadata**
  - **Validates: Requirements 1.3**

- [ ]* 2.4 Write property test for badge saturation levels
  - **Property 4: Low-saturation badge backgrounds**
  - **Validates: Requirements 1.4**

- [x] 3. Improve text contrast and readability
  - Update card subtitle color from #64748b to #94a3b8 for better contrast
  - Remove opacity layers, bake opacity into color values
  - Increase article count badge background opacity from 0.1 to 0.18
  - Add border to article count badge for better definition
  - Update all text colors to meet WCAG AA standards (4.5:1 minimum)
  - _Requirements: 2.1, 2.2, 2.3, 2.4_

- [ ]* 3.1 Write property test for text contrast compliance
  - **Property 6: Text contrast compliance**
  - **Validates: Requirements 2.1, 2.3**

- [ ]* 3.2 Write property test for badge luminance
  - **Property 7: Badge luminance distinction**
  - **Validates: Requirements 2.2**

- [ ]* 3.3 Write property test for UI element contrast
  - **Property 8: UI element contrast**
  - **Validates: Requirements 2.4**

- [x] 4. Optimize card spacing and layout
  - Increase card padding from 1.5rem to 1.75rem
  - Increase title container margin-bottom from 0.75rem to 1rem
  - Increase subtitle area margin-bottom from 0.5rem to 1rem
  - Increase metadata padding-top from 0.75rem to 1rem
  - Increase metadata-left gap from 0.75rem to 1rem
  - Increase metadata-right gap from 0.5rem to 0.625rem
  - _Requirements: 3.1, 3.3, 3.4_

- [ ]* 4.1 Write property test for card padding minimum
  - **Property 9: Card padding minimum**
  - **Validates: Requirements 3.1**

- [ ]* 4.2 Write property test for internal spacing
  - **Property 11: Internal spacing adequacy**
  - **Validates: Requirements 3.3**

- [ ]* 4.3 Write property test for metadata bottom spacing
  - **Property 12: Metadata bottom spacing**
  - **Validates: Requirements 3.4**

- [x] 5. Implement smart title processing
  - Create title processing utility function
  - Add logic to detect and remove "AWS re:Invent YYYY -" prefix
  - Update SummaryCard to use processed title for display
  - Preserve full original title in tooltip/title attribute
  - Add computed property for display title in LibraryView
  - _Requirements: 3.2, 7.1, 7.2, 7.5_

- [ ]* 5.1 Write property test for title prefix removal
  - **Property 10: Title prefix removal**
  - **Validates: Requirements 3.2, 7.1, 7.2**

- [ ]* 5.2 Write property test for title variation
  - **Property 27: Title variation in collections**
  - **Validates: Requirements 7.4**

- [ ]* 5.3 Write property test for title tooltip preservation
  - **Property 28: Title tooltip preservation**
  - **Validates: Requirements 7.5**

- [x] 6. Implement custom scrollbar styling
  - Add ::-webkit-scrollbar styles for Chrome/Safari/Edge
  - Set scrollbar width to 10px
  - Style scrollbar track with dark semi-transparent background
  - Style scrollbar thumb with slightly lighter color
  - Add smooth hover transition for thumb
  - Add Firefox scrollbar-width and scrollbar-color properties
  - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5_

- [ ]* 6.1 Write property test for scrollbar color darkness
  - **Property 13: Scrollbar color darkness**
  - **Validates: Requirements 4.2**

- [ ]* 6.2 Write property test for scrollbar transparency
  - **Property 14: Scrollbar transparency**
  - **Validates: Requirements 4.3**

- [ ]* 6.3 Write property test for scrollbar thumb contrast
  - **Property 15: Scrollbar thumb contrast**
  - **Validates: Requirements 4.4**

- [ ]* 6.4 Write property test for scrollbar hover subtlety
  - **Property 16: Scrollbar hover subtlety**
  - **Validates: Requirements 4.5**

- [x] 7. Refactor filter controls to filled style
  - Update CustomDropdown trigger to use filled background instead of outlined
  - Change background from transparent to rgba(51, 65, 85, 0.4)
  - Make border transparent by default
  - Update hover state to increase background opacity
  - Update focus state with subtle border and increased opacity
  - Ensure vertical center alignment in filter bar
  - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5_

- [ ]* 7.1 Write property test for filter vertical alignment
  - **Property 17: Filter vertical alignment**
  - **Validates: Requirements 5.1**

- [ ]* 7.2 Write property test for dropdown filled style
  - **Property 18: Dropdown filled style**
  - **Validates: Requirements 5.2**

- [ ]* 7.3 Write property test for filter visual weight
  - **Property 19: Filter visual weight consistency**
  - **Validates: Requirements 5.3**

- [ ]* 7.4 Write property test for filter baseline alignment
  - **Property 20: Filter baseline alignment**
  - **Validates: Requirements 5.4**

- [ ]* 7.5 Write property test for filter spacing
  - **Property 21: Filter spacing consistency**
  - **Validates: Requirements 5.5**

- [x] 8. Redesign logout button to neutral style
  - Remove red danger styling from logout button
  - Change to ghost button style with transparent background
  - Use neutral gray color (#94a3b8) for text/icon
  - Add subtle hover effect with low-opacity background
  - Ensure no red/orange hues in any button state
  - Reduce visual prominence compared to primary actions
  - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5_

- [ ]* 8.1 Write property test for logout button neutrality
  - **Property 22: Logout button neutrality**
  - **Validates: Requirements 6.1**

- [ ]* 8.2 Write property test for logout hover neutrality
  - **Property 23: Logout hover neutrality**
  - **Validates: Requirements 6.2**

- [ ]* 8.3 Write property test for logout visual de-emphasis
  - **Property 24: Logout visual de-emphasis**
  - **Validates: Requirements 6.3**

- [ ]* 8.4 Write property test for logout default subtlety
  - **Property 25: Logout default subtlety**
  - **Validates: Requirements 6.4**

- [ ]* 8.5 Write property test for logout interaction neutrality
  - **Property 26: Logout interaction neutrality**
  - **Validates: Requirements 6.5**

- [x] 9. Ensure code quality and maintainability
  - Audit all CSS class names for BEM compliance
  - Extract hardcoded colors to CSS custom properties
  - Verify all hover effects have transition properties
  - Ensure responsive spacing uses consistent scale (0.25rem multiples)
  - Add ARIA labels to interactive elements
  - Add keyboard navigation support where missing
  - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5_

- [ ]* 9.1 Write property test for BEM naming consistency
  - **Property 29: BEM naming consistency**
  - **Validates: Requirements 8.1**

- [ ]* 9.2 Write property test for CSS custom property usage
  - **Property 30: CSS custom property usage**
  - **Validates: Requirements 8.2**

- [ ]* 9.3 Write property test for transition definitions
  - **Property 31: Transition definition**
  - **Validates: Requirements 8.3**

- [ ]* 9.4 Write property test for responsive spacing scale
  - **Property 32: Responsive spacing scale**
  - **Validates: Requirements 8.4**

- [ ]* 9.5 Write property test for accessibility attributes
  - **Property 33: Accessibility attribute presence**
  - **Validates: Requirements 8.5**

- [x] 10. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 11. Update responsive styles for mobile
  - Verify all spacing changes work well on mobile breakpoints
  - Ensure custom scrollbar works on touch devices
  - Test filter controls remain usable on small screens
  - Verify card layout doesn't break with new spacing
  - Test title truncation on narrow screens
  - _Requirements: 3.1, 3.3, 3.4, 5.1, 5.2_

- [ ]* 11.1 Write integration tests for responsive behavior
  - Test card rendering at 320px, 768px, 1024px, 1920px widths
  - Verify spacing scales appropriately
  - Test filter controls remain accessible

- [x] 12. Add error handling and fallbacks
  - Add fallback colors for contrast calculation failures
  - Add fallback for custom scrollbar on unsupported browsers
  - Add error handling for title processing edge cases
  - Add placeholder text for missing card content
  - Log warnings for accessibility violations
  - _Requirements: 2.1, 2.2, 2.3, 4.1, 7.1_

- [ ]* 12.1 Write unit tests for error handling
  - Test color calculation fallbacks
  - Test title processing with malformed input
  - Test missing content handling

- [x] 13. Final checkpoint - Comprehensive testing
  - Ensure all tests pass, ask the user if questions arise.
