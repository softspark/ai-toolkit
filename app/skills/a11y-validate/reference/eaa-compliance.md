# European Accessibility Act (EAA) — Compliance Reference

Reference for `a11y-validate` Category 8e (EAA documentation). Legal framework, enforcement dates, member-state transposition deltas, and accessibility-statement templates.

**Not legal advice.** Consult counsel in your target jurisdiction.

## Directive (EU) 2019/882

**Full title**: Directive (EU) 2019/882 of the European Parliament and of the Council of 17 April 2019 on the accessibility requirements for products and services.

**Common name**: European Accessibility Act (EAA).

**Published**: Official Journal of the European Union, 7 June 2019.

**Adopted**: 17 April 2019.

**Deadline for member-state transposition into national law**: 28 June 2022.

**Deadline for business compliance**: **28 June 2025** (products placed on the market after this date; existing contracts up to 28 June 2030; self-service terminals already in use may have until 2045).

## Scope

### Products in scope (Article 2(1))

- Consumer general-purpose computer hardware and OS (desktops, laptops, tablets, smartphones).
- Self-service terminals: ATMs, ticket machines, check-in kiosks, interactive info points.
- Consumer terminal equipment with interactive computing capability (e.g., smart TVs, set-top boxes).
- E-readers.

### Services in scope (Article 2(2))

- Electronic communications (telephony, VoIP, text messaging).
- Services providing access to audiovisual media (streaming, VOD).
- **Elements of passenger transport services** (websites, mobile apps, ticketing, information services, e-tickets).
- Consumer banking services (online banking, mobile banking apps).
- E-books and dedicated e-book software.
- **E-commerce services** (online stores, marketplaces — consumer-facing).

### Out of scope

- Microenterprises (<10 employees AND <€2 million annual turnover) providing services. Still apply if selling products.
- Private websites/apps not providing covered services.
- B2B-only services.
- Pre-recorded AV media published before 28 June 2025.
- Content from third parties not controlled by the service provider.

## Legal Requirements (Chapter III)

### Article 4 — Accessibility requirements

Products and services must meet the accessibility requirements in **Annex I** of the directive. Annex I is intentionally functional/outcome-based (e.g., "information must be presentable in more than one sensory modality"). Technical implementation is defined by **harmonized standards** — primarily **EN 301 549 v3.2.1**, which aligns with WCAG 2.1 Level AA.

### Article 13 — Obligations of service providers

Service providers must:
1. Design and provide services in accordance with accessibility requirements.
2. Prepare the necessary information in the form of an **accessibility statement** in the general terms and conditions.
3. Preserve this information for as long as the service is in operation.

### Article 14 — Accessibility statement

The core documentary obligation. Statements must include:

1. A description of how the service meets the accessibility requirements.
2. If the service does not fully comply, the reasons for disproportionate burden or fundamental alteration claims.
3. Contact information for accessibility feedback.
4. Reference to the enforcement procedure in the user's member state.

Statements are typically published at a URL like `/accessibility` or `/accessibility-statement` and linked from the footer of every public page.

### Article 23 — Penalties

Member states define penalties. Typical ranges:

- **Germany (BFSG)**: up to €100,000 fine per violation; market surveillance authority: Bundesanstalt für Arbeitsschutz und Arbeitsmedizin (BAuA).
- **France (Loi 2023-171)**: up to €250,000 fine per violation; enforcement: Arcom + DGCCRF.
- **Italy (Legislative Decree 82/2022)**: fines between €5,000 and 5% of annual turnover; enforcement: AgID.
- **Spain (Royal Decree 193/2023)**: up to €1,000,000 fine; enforcement: Autoridad Independiente de Control Administrativo.
- **Netherlands (Uitvoeringswet)**: fines up to €103,000; enforcement: Agentschap Telecom.
- **Poland (Ustawa o zapewnianiu spełniania wymagań dostępności)**: fines up to 10× monthly average wage (~PLN 75,000); enforcement: Prezes Zarządu PFRON + UOKiK.

Beyond fines, regulators can order service withdrawal from the EU market.

## Harmonized Standard: EN 301 549 v3.2.1

Full title: "Accessibility requirements for ICT products and services."

Published by ETSI (European Telecommunications Standards Institute), CEN, and CENELEC. Current version: **v3.2.1**, March 2021.

**Compliance with EN 301 549 is presumed to satisfy the EAA.** Deviations require individual justification.

Structure:

| Chapter | Scope |
|---------|-------|
| 4 | General / generic requirements |
| 5 | Generic requirements on all ICT |
| 6 | ICT with two-way voice communication |
| 7 | ICT with video capabilities |
| 8 | Hardware |
| 9 | Web (full WCAG 2.1 AA) |
| 10 | Non-web documents (PDF, etc.) |
| 11 | Software (native apps — mobile, desktop) |
| 12 | Documentation and support services |
| 13 | ICT providing relay / emergency services |

For websites and mobile apps, chapters 9 and 11 are most relevant.

## Timeline

| Date | Event |
|------|-------|
| 17 April 2019 | Directive adopted |
| 7 June 2019 | Published in Official Journal |
| 28 June 2022 | Member-state transposition deadline |
| **28 June 2025** | **Business compliance deadline — products/services placed on market** |
| 28 June 2030 | End of transition for existing contracts |
| 28 June 2045 | Outer limit for self-service terminals in service before 2025 |

**If you are selling to EU consumers and reading this after 28 June 2025: you are already required to comply.**

## Accessibility Statement Template

Most member states publish an official template. Common structural elements (minimum):

```markdown
# Accessibility Statement

[Organization name] is committed to making [service name / website URL] accessible in accordance with [Directive (EU) 2019/882 / national transposing law, e.g., Loi 2023-171 for France].

## Conformance Status

This [website / mobile application] is **[fully | partially | non-]compliant** with [EN 301 549 v3.2.1 / WCAG 2.1 Level AA].

[If partially / non-compliant:] The following content is not accessible:

- [Non-conformant element 1 — e.g., "PDF invoices from before 2023 lack tagged structure"]
- [Non-conformant element 2]

These non-conformances are due to [disproportionate burden reasoning / third-party content / technology limitations].

## Preparation of This Statement

This statement was prepared on [ISO date, e.g., 2025-06-15] and last reviewed on [date].

The assessment method was:
- [self-assessment / third-party audit by <firm>]
- [manual testing / automated tooling: axe-core, Lighthouse, Pa11y]
- [assistive technology testing: NVDA, JAWS, VoiceOver, TalkBack]

## Feedback and Contact Information

If you encounter any accessibility barriers on [service name], please contact us:

- Email: [accessibility@example.com]
- Phone: [+XX ...]
- Postal: [address]

We aim to respond within [14 days / as per national requirement].

## Enforcement Procedure

If you are not satisfied with our response, you may contact the national enforcement body:

- [Member state enforcement body name]
- [URL / phone / email]

## Technical Specifications

Accessibility of [service] relies on the following technologies:

- HTML5
- CSS
- JavaScript
- [WAI-ARIA 1.2]
- [PDF/UA for document accessibility]
```

## Member-State Enforcement URLs (to cite in statements)

Replace placeholders in statement templates with these URLs:

| Member state | Enforcement body | URL |
|---|---|---|
| Austria | Sozialministeriumservice (BSB) | https://www.sozialministeriumservice.at/ |
| Belgium | BOSA DG for Digital Transformation | https://bosa.belgium.be/ |
| Bulgaria | Ministry of Transport and Comms | https://www.mtc.government.bg/ |
| Croatia | Ministry of Physical Planning | https://mpgi.gov.hr/ |
| Cyprus | Department for Social Inclusion | http://www.mlsi.gov.cy/ |
| Czechia | Ministry of Industry and Trade | https://www.mpo.gov.cz/ |
| Denmark | Digitaliseringsstyrelsen | https://digst.dk/ |
| Estonia | Riigi Infosüsteemi Amet (RIA) | https://www.ria.ee/ |
| Finland | Regional State Administrative Agency | https://www.saavutettavuusvaatimukset.fi/ |
| France | Arcom + DGCCRF | https://www.arcom.fr/ |
| Germany | BFIT-Bund | https://www.bfit-bund.de/ |
| Greece | General Secretariat for Digital Governance | https://gov.gr/ |
| Hungary | Nemzeti Média- és Hírközlési Hatóság (NMHH) | https://nmhh.hu/ |
| Ireland | National Disability Authority (NDA) | https://nda.ie/ |
| Italy | AgID | https://www.agid.gov.it/ |
| Latvia | Ministry of Welfare | https://www.lm.gov.lv/ |
| Lithuania | Ministry of Social Security | https://socmin.lrv.lt/ |
| Luxembourg | SIP (Service information et presse) | https://sip.gouvernement.lu/ |
| Malta | Commission for the Rights of Persons with Disabilities (CRPD) | https://www.crpd.org.mt/ |
| Netherlands | Agentschap Telecom | https://www.agentschaptelecom.nl/ |
| Poland | PFRON + UOKiK | https://www.pfron.org.pl/ |
| Portugal | AMA (Agência para a Modernização Administrativa) | https://www.ama.gov.pt/ |
| Romania | Autoritatea Națională pentru Drepturile Persoanelor cu Dizabilități | https://andpdca.gov.ro/ |
| Slovakia | Ministry of Investments, Regional Development and Informatization | https://www.mirri.gov.sk/ |
| Slovenia | Ministry of Public Administration | https://www.gov.si/ |
| Spain | Autoridad Independiente de Control Administrativo | https://administracionelectronica.gob.es/ |
| Sweden | Myndigheten för digital förvaltning (DIGG) | https://www.digg.se/ |

## Common Member-State Route Conventions

The skill detects accessibility statements at any of these URL patterns:

- `/accessibility` — English (generic)
- `/accessibility-statement` — English (explicit)
- `/a11y` — English (shortform)
- `/dostepnosc` — Polish
- `/deklaracja-dostepnosci` — Polish (fuller)
- `/barrierefreiheit` — German
- `/barrierefreiheitserklaerung` — German (fuller)
- `/declaration-accessibilite` — French
- `/declaración-accesibilidad` — Spanish
- `/dichiarazione-accessibilita` — Italian
- `/dichiarazione-di-accessibilita` — Italian (fuller)
- `/toegankelijkheidsverklaring` — Dutch
- `/tilgangelighetserklaering` — Norwegian (non-EU but adjacent)
- `/tillganglighetsutlatande` — Swedish
- `/saavutettavuusseloste` — Finnish
- `/prohlaseni-o-pristupnosti` — Czech
- `/vyhlasenie-o-pristupnosti` — Slovak
- `/nyilatkozat-az-akadalymentesitesrol` — Hungarian

## Accessibility Conformance Report (ACR) / VPAT

Beyond the public accessibility statement, many organizations produce a machine-readable or structured **Accessibility Conformance Report** — often using the **VPAT® 2.5 Rev** template (Voluntary Product Accessibility Template) from the Information Technology Industry Council (ITI).

VPAT sections for EU markets use the "INT" or "EU" variant, which maps to EN 301 549.

VPAT is not legally required under EAA but is common in B2B / procurement contexts.

Template: https://www.itic.org/policy/accessibility/vpat

## References

- EAA directive (full text): https://eur-lex.europa.eu/eli/dir/2019/882/oj
- EN 301 549 v3.2.1 (PDF): https://www.etsi.org/deliver/etsi_en/301500_301599/301549/03.02.01_60/en_301549v030201p.pdf
- European Commission EAA page: https://ec.europa.eu/social/main.jsp?catId=1202
- W3C WAI EAA overview: https://www.w3.org/WAI/policies/european-union/#eaa
- W3C accessibility statement generator: https://www.w3.org/WAI/planning/statements/generator/
