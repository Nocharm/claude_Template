import { buildTtsUrl, cleanForSpeech } from "./speech";

describe("speech helpers", () => {
  it("drops study placeholders before speaking", () => {
    expect(cleanForSpeech("have always been ~")).toBe("have always been");
    expect(cleanForSpeech("catch  sight of ~ something")).toBe("catch sight of something");
  });

  it("builds an encoded, cacheable TTS URL", () => {
    expect(buildTtsUrl("I'm down & ready", "au", true)).toBe(
      "/api/tts?text=I%27m+down+%26+ready&accent=au&slow=true",
    );
  });
});
