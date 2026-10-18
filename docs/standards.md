# Standards mapping

What this tool takes from configuration management standards, and what
it does not claim. This tool is not certified against, compliant with,
or endorsed by any of these standards. The mapping is design rationale:
it explains why the tool is shaped the way it is, so a reader can judge
whether that shape fits their process. The standard texts themselves are
paywalled; clause titles and principle codes below come from the
secondary sources listed at the end, and are labeled as such.

## Terms used here

- **Configuration item (CI).** An entity within a configuration that
  satisfies an end use function (ISO 10007 wording, via the Wikipedia
  summary). In this tool, the unit is the CI and the change is the
  proposed alteration to it.
- **Configuration baseline.** Approved configuration information that
  establishes the characteristics of a product at a point in time and
  serves as reference for activities through the life cycle (ISO 10007
  wording, via the same summary). This tool does not hold a baseline.
  It classifies pairs against inputs the caller supplies.
- **Applicability.** Which items a change concerns at all, usually by
  program, variant, or configuration. Distinct from effectivity.
- **Effectivity.** When, or for which units in a series, a change
  applies: a range, a date, a lot, or a serial span. This tool models
  effectivity as an inclusive range over ordered keys (ADR 0001).

## ISO 10007:2017, Quality management, Guidelines for configuration management

Clause structure below follows the clause table published by Pacific
Cert (a secondary source). ISO 10007 gives guidance, not requirements,
and is meant to support the product identification and traceability
requirements of ISO 9001:2015.

| ISO 10007 clause | What this tool does | What it does not do |
|---|---|---|
| 4 Configuration management principles | Planning, identification, control, status accounting, audits are kept as separate concerns: docs, resolver, log, verify | Nothing; the tool is not a CM system |
| 5 Configuration management planning | ADRs record the decisions; LIMITS records what is out of scope | No CM plan; no roles or responsibilities |
| 6 Configuration identification | Units, changes, material, incorporations are typed, validated, and identified by stable ids | No baseline management; no CI hierarchy |
| 7 Configuration change control | Applicability (ADR 0004) and the exactly-one-match rule force competing changes to be disposed of by a human instead of silently resolved | No approval workflow; no change board; a human still signs incorporation |
| 8 Configuration status accounting | The append-only run log records rule version, input hash, counts, and every decision; verify audits the log | No hash chain, no signature; the log is not tamper-evident (ADR 0005) |
| 9 Configuration audits | Decision traces show why each decision fired; the conflict pass names every competing change | No functional or physical configuration audit (FCA/PCA). The tool never checks that a built unit matches its documentation |

Two audit types from the same secondary source are worth naming
because they bound this tool: a Functional Configuration Audit verifies
that the functional characteristics of a CI have been achieved, and a
Physical Configuration Audit verifies that the physical characteristics
as documented match the product as manufactured. This tool does
neither. It classifies paperwork, not hardware.

## SAE/EIA-649C, National Consensus Standard for Configuration Management

The five functions, per secondary summaries of the standard: CM
planning, configuration identification, change management
(configuration control), configuration status accounting, and
configuration verification and audit. Three principles from the
standard, quoted via the CMStat article on EIA-649, shaped specific
choices:

- **CSA-1.** Configuration Status Accounting provides an accurate,
  timely information base concerning a product and its product
  configuration information throughout the product life cycle. This is
  why the log records every decision with its input hash instead of
  only a summary, and why verification recomputes counts from the
  decisions on each line.
- **CVA-3.** Verify implementation of each change to ensure
  consistency is maintained between the product, its configuration
  information, and related support assets. This is why the resolver
  checks incorporation records against hold position and material
  state instead of trusting any one of them alone, and why a
  contradictory incorporation record (R03) stays visible as a data
  error instead of being smoothed over.
- **CMP-8.** Performing configuration management includes
  responsibility for the configuration management performance of the
  supply chain. This tool does not manage suppliers, but it does treat
  supplier-facing state (material staged at the work, material
  installed) as first-class input, and it refuses to guess when that
  state contradicts the incorporation record.

EIA-649 lists "engineering change effectivity" among the typical
status accounting information tracked across the product life cycle
(Table 5 in the EIA-649 text, per the PPPL-hosted copy). That is the
closest the standard comes to naming this tool's job: effectivity is
status accounting information, not a decision the change form makes by
itself.

## ISO 10303-242:2022 (AP242), Managed model based 3D engineering

AP242 is the STEP application protocol for managed model-based 3D
engineering (Edition 3, 2022, per the ISO catalog page). Its scope
includes, per that page: product definition data and configuration
control data for managing large numbers of variants of products during
the design phase; data describing the changes that have occurred during
the design phase, including tracking of the versions of a product and
of the data related to the documentation of the change process; release
and approval data for product data; and identification of physically
realized parts or tools.

What this tool takes from that scope:

- **Variants.** AP242 treats variant management as configuration
  control data. The applicability layer (ADR 0004) is this tool's
  variant mechanism: one change, different applicability per program.
  It is a deliberately small version: program strings, not a product
  structure.
- **Change tracking.** AP242 tracks versions of a product and the
  documentation of the change process. This tool tracks decisions per
  run with an input hash, not versions of a product. It has no
  revision history for a change.
- **Release and approval.** AP242 carries release and approval data.
  This tool carries none: an incorporation record says work is done,
  not that it was approved, and nothing here authorizes work.

What this tool does not take: geometry, PMI, assemblies, or any CAD
content. It is not an AP242 reader, writer, or validator. If AP242
effectivity (dated, lot, or serial effectivity in STEP data) is ever
an input, it arrives as CSV after someone else extracts it.

## Applicability versus effectivity

The two terms are often collapsed; the tool keeps them separate because
collapsing them hides real mistakes:

- **Applicability** is about which configuration a change concerns.
  In configurator usage, a publication has applicability dates and a
  model has effectivity dates on its nodes and rules (Oracle
  Configurator guide). In this tool, applicability is the (change,
  program) table.
- **Effectivity** is about when, or for which units, a rule or change
  is valid. Configit describes effectivity as defining when
  information such as configuration rules is valid, and notes that
  effectivity and versioning go hand in hand to manage changes over
  time. In this tool, effectivity is the inclusive key range (R01)
  plus the hold point comparison (R05 to R07).

A change can be applicable but out of effectivity (right program,
wrong serial range), or in effectivity but not applicable (right serial
range, wrong program). Both cases must be visible, which is why the
extended report lists excluded pairs instead of dropping them quietly.

## What this tool deliberately does not model

- **Revision and supersession as history.** Supersession rows are
  declarations that one change replaces another (ADR 0004). The tool
  does not keep a revision history, does not bump revisions, and does
  not retire a change on the strength of a declaration.
- **Dates.** Effectivity here is key order, not calendar time. Dated
  effectivity (a change effective from a date) is not modeled; the
  decision function takes no clock (ADR 0002).
- **As-built versus as-designed.** The tool classifies against
  caller-supplied as-built state (hold points, material, incorporation
  records). It cannot check that state against design intent, because
  it never sees design intent.
- **Authority.** Nothing here approves, releases, or authorizes work.
  A human signs incorporation. The tool classifies.

## Sources consulted

- ISO 10007:2017, Quality management, Guidelines for configuration
  management. Clause titles and the FCA/PCA descriptions via Pacific
  Cert, "ISO 10007:2017 Quality Management, Configuration Management"
  and "ISO 10007 Guide, Configuration Management in Projects"
  (pacificcert.com, blog.pacificcert.com). Term definitions via the
  Wikipedia summary of ISO 10007.
- SAE/EIA-649C, National Consensus Standard for Configuration
  Management. Five functions via secondary overviews; principles
  CSA-1, CVA-3, CMP-8 via CMStat, "An Example Use of Configuration
  Management and the EIA-649 Standard During the COVID-19 Emergency"
  (cmstat.com). Table 5 via the EIA-649 text hosted by PPPL
  (ncsx.pppl.gov).
- ISO 10303-242:2022, Industrial automation systems and integration,
  Product data representation and exchange, Part 242: Application
  protocol: Managed model-based 3D engineering. Scope via the ISO
  catalog page (iso.org, Edition 3, 2022).
- SEBoK, "Configuration Management" (sebokwiki.org): CM applies to
  hardware, software, services, and systems of systems, and the
  article aligns its account with INCOSE, ISO 10007, and SAE EIA-649C.
- Configit, "Rule History Management" (configit.com): effectivity
  defines when information is valid; effectivity and versioning
  together manage changes over time.
- Oracle Configurator Developer User's Guide (docs.oracle.com):
  effectivity start and end dates on model nodes and rules,
  publication applicability dates.
