# Legal Sources Documentation

## Overview
This document provides proper attribution and access information for all legal documents used in the Bedrock Legal AI Project. Raw PDFs are not included in this repository to respect copyright. Instead, we provide structured data and processing scripts.

## Legal Framework Coverage

### United States Federal Law

#### Criminal Code (Title 18)
- **Source**: United States Code, Title 18 - Crimes and Criminal Procedure
- **Access Method**: Official U.S. Government Publishing Office (GPO)
- **URL**: https://www.govinfo.gov/app/collection/uscode
- **Relevance**: Federal criminal law framework for digital services

#### CSAM Reporting Requirements
- **Source**: 18 U.S.C. § 2258A - Reporting requirements for electronic communication service providers
- **Access Method**: Official U.S. Government Publishing Office (GPO)
- **URL**: https://www.govinfo.gov/content/pkg/USCODE-2023-title18/html/USCODE-2023-title18-partI-chap110-sec2258A.htm
- **Relevance**: Child safety and content moderation requirements

#### Recent Federal Legislation
- **Source**: Public Law 118-59 (118th Congress)
- **Access Method**: Congress.gov
- **URL**: https://www.congress.gov/bill/118th-congress
- **Relevance**: Recent federal legislative developments

### State Legislation

#### California
- **California Senate Bill 472 (2019)**: Social media regulation
- **California Senate Bill 985 (2022)**: Digital privacy protections
- **California Assembly Bill 1501 (2023)**: Online safety measures
- **California Assembly Bill 157 (2024)**: Digital services regulation
- **California Civil Code § 1798.99.33**: Privacy protections
- **California Health & Safety Code § 111926**: Health-related regulations
- **California Revenue & Taxation Code § 23691**: Tax-related provisions
- **California Rules of Court, Rule 2.1040**: Court procedures

**Access Method**: California Legislative Information
**URL**: https://leginfo.legislature.ca.gov/

#### Florida
- **Florida House Bill 3 (2024)**: Online protections for minors
- **Source**: Florida Statutes
- **Access Method**: Florida Legislature
- **URL**: https://www.flsenate.gov/

#### Utah
- **Utah Senate Bill 152 (2023)**: Social media regulation amendments
- **Utah House Bill 311 (2023)**: Social media usage amendments
- **Utah Code Ann. § 76-5b-206**: Criminal code provisions
- **Source**: Utah State Legislature
- **Access Method**: Utah Legislature
- **URL**: https://le.utah.gov/

### European Union Law

#### Digital Services Act (DSA)
- **Source**: EU Regulation 2022/2065
- **Official Journal**: OJ L 277, 27.10.2022, p. 1–102
- **Access Method**: EUR-Lex (Official EU Law Portal)
- **URL**: https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX%3A32022R2065
- **Relevance**: EU digital services regulation framework

### Case Law and Legal Proceedings

#### Federal Court Cases
- **NetChoice, LLC v. Griffin (2025)**: Social media regulation litigation
- **Source**: U.S. District Court
- **Access Method**: PACER (Public Access to Court Electronic Records)
- **Relevance**: Constitutional challenges to social media regulation

- **NetChoice v. Bonta (2024)**: California social media regulation challenge
- **Source**: U.S. District Court
- **Access Method**: PACER
- **Relevance**: State regulation constitutionality

- **Doe v. Roblox Corp. (2024)**: Platform liability case
- **Source**: U.S. District Court
- **Access Method**: PACER
- **Relevance**: Platform responsibility for user content

#### Legal Proceedings
- **In re Social Media Adolescent Addiction Personal Injury Proceedings**
- **Source**: Multi-district litigation
- **Access Method**: Federal court records
- **Relevance**: Social media harm litigation

### Academic and Research Sources

#### EU Research
- **EPRS Briefing (2025)**: European Parliamentary Research Service
- **Source**: European Parliament
- **Access Method**: EPRS Publications
- **URL**: https://www.europarl.europa.eu/thinktank/

#### Academic Papers
- **Kingma-Daan TikTok Report (2023)**: Academic analysis
- **Source**: Academic research
- **Access Method**: University library databases
- **Relevance**: Social media platform analysis

## Data Processing Approach

### Structured Data Format
Instead of raw PDFs, we use structured JSON format:

```json
{
  "law_name": "California Senate Bill 472",
  "jurisdiction": "California",
  "year": 2019,
  "article": "Section 1",
  "clause": "Legislative findings",
  "content": "The Legislature finds and declares...",
  "source": "California Legislative Information",
  "access_date": "2025-08-30",
  "url": "https://leginfo.legislature.ca.gov/"
}
```

### Processing Scripts
- **`batch_pdf_to_jsonl.py`**: Converts PDFs to structured format
- **`convert_techjam_append.py`**: Processes legal data for training
- **`create_gold_dataset.py`**: Creates training datasets

### Training Data
- **Format**: JSONL (JSON Lines)
- **Content**: Extracted legal snippets with proper attribution
- **Size**: 741+ training examples
- **Coverage**: Multi-jurisdiction legal framework

## Copyright Compliance

### Fair Use Principles
- **Purpose**: Educational and research use
- **Nature**: Legal documents (factual content)
- **Amount**: Short excerpts and structured data only
- **Effect**: No commercial impact on copyright holders

### Attribution Requirements
- **Source**: Always cite original source
- **Access Method**: Document how to access original
- **Date**: Include access date
- **URL**: Provide direct links where available

### Data Usage
- **Training**: Use structured data for model training
- **Testing**: Include sample excerpts for validation
- **Documentation**: Maintain comprehensive source tracking

## Repository Structure

```
bedrock/
├── LEGAL_SOURCES.md          # This file - source documentation
├── batch_pdf_to_jsonl.py     # PDF processing script
├── convert_techjam_append.py # Data conversion script
├── create_gold_dataset.py    # Dataset creation script
├── sagemaker-finetune/
│   └── data/
│       ├── train_refined_v4.jsonl    # Training data
│       └── validation.jsonl          # Validation data
└── docs/                     # Project documentation
```

## Access Instructions

### For Researchers
1. **Use official sources**: Access documents through official government portals
2. **Follow attribution**: Cite sources properly in any derived work
3. **Respect copyright**: Don't redistribute raw PDFs
4. **Use structured data**: Work with our processed JSONL format

### For Developers
1. **Clone repository**: `git clone https://github.com/Arnie016/Tiktok-TECHJAM.git`
2. **Use training data**: Access processed data in `sagemaker-finetune/data/`
3. **Run processing scripts**: Convert your own PDFs to structured format
4. **Maintain attribution**: Document sources in your work

### For Legal Professionals
1. **Verify sources**: Always check against official versions
2. **Use current versions**: Laws may have been updated since processing
3. **Consult experts**: This is not legal advice
4. **Follow jurisdiction**: Apply appropriate legal framework

## Updates and Maintenance

### Version Control
- **Source tracking**: All sources documented with dates
- **Update process**: Regular review of legal changes
- **Version history**: Track changes in legal frameworks

### Quality Assurance
- **Source verification**: Cross-reference with official sources
- **Content accuracy**: Validate extracted content
- **Attribution completeness**: Ensure all sources properly cited

## Contact and Support

For questions about legal sources or data processing:
- **Repository Issues**: Use GitHub Issues
- **Legal Questions**: Consult qualified legal professionals
- **Technical Support**: Review documentation in `/docs/`

---

**Disclaimer**: This documentation is for educational and research purposes only. It does not constitute legal advice. Always consult official sources and qualified legal professionals for legal matters.
