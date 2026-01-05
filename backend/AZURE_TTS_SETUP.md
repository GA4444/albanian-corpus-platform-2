# Azure TTS Setup për Gjuhën Shqipe (Albanian)

Ky dokument shpjegon se si të konfiguroni **Azure Text-to-Speech** për zëra neural profesionalë në gjuhën shqipe.

## Përse Azure TTS?

- ✅ **Zëra Neural** — Shumë më të natyrshëm sesa gTTS
- ✅ **Cilësi e lartë** — 24kHz audio, i përshtatshëm për fëmijë
- ✅ **Zëra shqip** — `sq-AL-AnilaNeural` (femër) dhe `sq-AL-IlirNeural` (mashkull)
- ✅ **Kontroll i plotë** — Shpejtësi, intonacion, volum, pauzë
- ✅ **Fallback automatik** — Nëse nuk është konfiguruar, përdor gTTS

## Hapat për Konfigurimin

### 1. Krijoni një llogari Azure (nëse nuk keni)

1. Shkoni te [portal.azure.com](https://portal.azure.com)
2. Regjistrohuni ose identifikohuni
3. Zgjidhni "Create a resource" → "AI + Machine Learning" → "Speech"

### 2. Merrni çelësin dhe rajonin

1. Pas krijimit të shërbimit "Speech", shkoni te "Keys and Endpoint"
2. Kopjoni:
   - **Key 1** ose **Key 2**
   - **Region** (p.sh., `westeurope`, `eastus`, etj.)

### 3. Vendosni variablat e mjedisit

Krijoni ose përditësoni file-in `.env` në direktorinë `backend/`:

```bash
# Azure TTS Configuration (optional - falls back to gTTS if not set)
AZURE_SPEECH_KEY=your_azure_speech_key_here
AZURE_SPEECH_REGION=westeurope  # or your region
```

**Shënim**: Nëse nuk vendosni këto variabla, platforma do të përdorë gTTS automatikisht.

### 4. Instaloni librarinë

```bash
cd backend
pip install azure-cognitiveservices-speech==1.34.0
```

Ose:

```bash
pip install -r requirements.txt
```

### 5. Testoni

Ristartoni backend-in:

```bash
cd backend
uvicorn app.main:app --reload
```

Testoni me një API call:

```bash
curl -X POST "http://localhost:8000/api/text-to-speech" \
  -H "Content-Type: application/json" \
  -d '{"text": "Mirëdita, si jeni?", "voice": "anila"}'
```

Ose:

```bash
curl "http://localhost:8000/api/audio-exercises/1?voice=anila"
```

## Zërat e Disponueshëm

| Emri      | ID                    | Gjinia | Përshkrimi                                    |
|-----------|-----------------------|--------|-----------------------------------------------|
| **Anila** | `sq-AL-AnilaNeural`   | Femër  | I ngrohtë, i qartë — i rekomanduar për fëmijë |
| **Ilir**  | `sq-AL-IlirNeural`    | Mashkull | Autoritativ, profesional                     |

## Parametrat e Avancuar

### Shpejtësia (Rate)

- `"+0%"` — Normal (default)
- `"-15%"` — Më ngadalë (për diktim)
- `"+20%"` — Më shpejt

### Intonacioni (Pitch)

- `"+0Hz"` — Normal (default)
- `"-2Hz"` — Më i ulët
- `"+5Hz"` — Më i lartë

### Shembull API Call me Parametra

```bash
curl -X POST "http://localhost:8000/api/text-to-speech" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Ky është një ushtrim drejtshkrimi.",
    "voice": "anila",
    "rate": "-10%",
    "pitch": "+2Hz"
  }'
```

## Çmimi (Azure)

- **Free Tier**: 5 milion karaktere/muaj falas për neural voices
- **Standard**: ~$16 për 1 milion karaktere

Për një platformë edukative me ~1000 përdorues aktivë, free tier është mjaftueshëm.

## Fallback në gTTS

Nëse Azure nuk është konfiguruar ose ndodh një gabim, sistemi bie automatikisht mbrapsht në **gTTS** (Google Text-to-Speech), që është falas por me cilësi më të ulët.

## Support

Për probleme me Azure TTS, kontaktoni:
- [Azure Speech Documentation](https://learn.microsoft.com/en-us/azure/ai-services/speech-service/)
- [Supported Languages (Albanian)](https://learn.microsoft.com/en-us/azure/ai-services/speech-service/language-support?tabs=tts)

---

**Shënim**: Për platforma akademike/kërkimore, Microsoft ofron **Azure for Students** me kredite falas.
