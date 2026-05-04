React re-renders all children when the parent renders, even if props are unchanged. To skip:

- Wrap child in `React.memo()` — shallow prop compare
- `useMemo` for object/array props (new reference defeats memo)
- `useCallback` for function props (same reason)
