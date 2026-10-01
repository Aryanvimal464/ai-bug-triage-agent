# Accuracy Report

Test bugs: 12

| Metric | Correct | Accuracy |
|---|---|---|
| Severity (exact) | 0/12 | 0% |
| Severity (within 1 level) | 0/12 | 0% |
| Module | 0/12 | 0% |
| Duplicate detection | 6/12 | 50% |

## Wrong predictions

- **T1**: expected Critical/Login/dup=yes -> got //dup=no
- **T2**: expected High/Cart/dup=yes -> got //dup=no
- **T3**: expected High/Order Tracking/dup=no -> got //dup=no
- **T4**: expected Critical/Checkout/dup=yes -> got //dup=no
- **T5**: expected Medium/Signup/dup=no -> got //dup=no
- **T6**: expected Medium/Login/dup=yes -> got //dup=no
- **T7**: expected High/Search/dup=no -> got //dup=no
- **T8**: expected Low/General/dup=no -> got //dup=no
- **T9**: expected Critical/Checkout/dup=no -> got //dup=no
- **T10**: expected High/Order Tracking/dup=yes -> got //dup=no
- **T11**: expected Low/Profile/dup=no -> got //dup=no
- **T12**: expected High/Login/dup=yes -> got //dup=no