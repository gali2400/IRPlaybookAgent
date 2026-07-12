# MedBridge Health Systems — Security Context

## Organization Overview
MedBridge Health Systems is a 1,200-employee healthcare organization in the Atlanta metropolitan area
operating 6 facilities including 2 hospitals and 4 outpatient clinics. The organization serves 340,000
patients and is subject to HIPAA and HITECH regulations.

## IT Environment
- **Architecture:** Hybrid (Microsoft Azure + On-Premises)
- **EHR System:** Epic EHR (APP-001 primary, APP-002 DR) — contains full patient records for 340,000 patients
- **Identity:** Azure Active Directory / Entra ID
- **Endpoints:** 492 managed endpoints (Windows 10/11 via SCCM)
- **Servers:** 40 Windows servers, 12 Linux servers
- **Network:** Cisco ASA 5555-X perimeter firewall (EOL as of 2024, no active support contract)
- **Cloud:** Microsoft Azure (Azure Blob Storage AZ-005 for radiology archive, Azure AD, O365)
- **Integration Engine:** Rhapsody (RHAPSODY-01) for HL7 lab data exchange

## Key Systems
| System | Description | PHI? |
|--------|-------------|------|
| Epic EHR (APP-001/002) | Primary patient records system | Yes — 340,000 records |
| Active Directory (AD-DC-01/02) | Identity and access management | No |
| Rhapsody (RHAPSODY-01) | HL7 integration engine to LabConnect | Partial |
| Azure Blob (AZ-005) | Radiology DICOM archive via RadCloud | Yes — imaging PHI |
| Cisco ASA 5555-X (NET-001) | Perimeter firewall (EOL 2024) | No |

## Known Security Gaps (Critical for IR Context)
- **No CISO** — IT Director handles all security decisions reactively
- **No SIEM** — Windows Event Logs not centrally aggregated; no centralized log review
- **No EDR** — Windows Defender Antivirus only; no behavioral detection
- **MFA at 35%** — Clinical staff enrollment only 12%; admin staff higher
- **No PAM** — 14 domain admin accounts used for daily work; 127 unmanaged service accounts
- **No IRP update since Dec 2021** — No ransomware, insider threat, or cloud playbooks
- **BCP untested since June 2020** — Epic backup recovery never validated; no defined RTO/RPO
- **120 medical devices** (Baxter Sigma infusion pumps) with default credentials on VLAN 40

## Third-Party Vendors
| Vendor | Service | Connection | Risk |
|--------|---------|-----------|------|
| LabConnect | HL7 lab integration | Site-to-site VPN (PSK not rotated 4 years, no MFA) | High |
| RadCloud | DICOM radiology archive | HTTPS API (static API key, SOC 2 Type I only) | Medium |
| PaySync | Payment processing | HTTPS API | Low |

## Prior Incidents
- **INC-2023-001** — AiTM credential phishing; 3 accounts compromised; 6-hour MTTD
- **INC-2024-001** — Malware on clinical workstation; 72-hour dwell time before detection; no EDR
- **INC-2024-002** — Azure Blob Storage misconfiguration; 12 hours PHI exposure; no CSPM

## HIPAA Breach Notification Requirements
- HHS notification required within **60 days** of discovering a breach
- Individual notification required within **60 days**
- Media notification if **500+ individuals** in same state are affected
- Georgia Personal Identity Protection Act: **30-day** state notification window
- Small breach log: <500 individuals — submit annually to HHS
