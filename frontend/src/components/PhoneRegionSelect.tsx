const PHONE_REGIONS = (
  "NO,SE,DK,FI,IS,AC,AD,AE,AF,AG,AI,AL,AM,AO,AR,AS,AT,AU,AW,AX,AZ,BA,BB,BD,BE,BF,BG,BH,BI,BJ,BL,BM,BN,BO,BQ,BR,BS,BT,BW,BY,BZ,CA,CC,CD,CF,CG,CH,CI,CK,CL,CM,CN,CO,CR,CU,CV,CW,CX,CY,CZ,DE,DJ,DM,DO,DZ,EC,EE,EG,EH,ER,ES,ET,FJ,FK,FM,FO,FR,GA,GB,GD,GE,GF,GG,GH,GI,GL,GM,GN,GP,GQ,GR,GT,GU,GW,GY,HK,HN,HR,HT,HU,ID,IE,IL,IM,IN,IO,IQ,IR,IT,JE,JM,JO,JP,KE,KG,KH,KI,KM,KN,KP,KR,KW,KY,KZ,LA,LB,LC,LI,LK,LR,LS,LT,LU,LV,LY,MA,MC,MD,ME,MF,MG,MH,MK,ML,MM,MN,MO,MP,MQ,MR,MS,MT,MU,MV,MW,MX,MY,MZ,NA,NC,NE,NF,NG,NI,NL,NP,NR,NU,NZ,OM,PA,PE,PF,PG,PH,PK,PL,PM,PR,PS,PT,PW,PY,QA,RE,RO,RS,RU,RW,SA,SB,SC,SD,SG,SH,SI,SJ,SK,SL,SM,SN,SO,SR,SS,ST,SV,SX,SY,SZ,TA,TC,TD,TG,TH,TJ,TK,TL,TM,TN,TO,TR,TT,TV,TW,TZ,UA,UG,US,UY,UZ,VA,VC,VE,VG,VI,VN,VU,WF,WS,XK,YE,YT,ZA,ZM,ZW"
).split(",");

const REGION_LABELS: Record<string, string> = {
  NO: "Norge",
  SE: "Sverige",
  DK: "Danmark",
  FI: "Finland",
  IS: "Island",
  GB: "Storbritannia",
  US: "USA",
};

type PhoneRegionSelectProps = {
  value: string;
  onChange: (value: string) => void;
  disabled?: boolean;
  ariaLabel?: string;
};

export function PhoneRegionSelect({
  value,
  onChange,
  disabled = false,
  ariaLabel = "Land/region for telefonnummer",
}: PhoneRegionSelectProps) {
  return (
    <select
      aria-label={ariaLabel}
      value={value}
      onChange={(event) => onChange(event.target.value)}
      disabled={disabled}
    >
      <option value="">Velg land/region</option>
      {PHONE_REGIONS.map((region) => (
        <option key={region} value={region}>
          {REGION_LABELS[region] ? `${REGION_LABELS[region]} (${region})` : region}
        </option>
      ))}
    </select>
  );
}

export function initialPhoneRegion(
  phone: string | null | undefined,
  regionUsed: string | null | undefined,
  tenantDefault: string | null | undefined,
): string {
  if ((phone ?? "").trim().startsWith("+")) return "";
  return regionUsed ?? tenantDefault ?? "";
}
