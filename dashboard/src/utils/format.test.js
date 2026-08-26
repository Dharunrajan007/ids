// Unit tests for the dashboard's pure logic (vitest, no DOM needed).
// The theme: malformed or partial API data must degrade, never throw.

import { describe, expect, it } from "vitest";

import {
  alertsFrom,
  attackMeta,
  buildTimelineData,
  buildTypeChartData,
  confidencePercent,
  sameRecord,
  timeOfDay,
} from "./format.js";

describe("attackMeta", () => {
  it("maps the four known categories", () => {
    expect(attackMeta("dos").label).toBe("DoS");
    expect(attackMeta("u2r").label).toBe("U2R");
  });

  it("renders unknown categories honestly instead of crashing", () => {
    expect(attackMeta("zero_day").label).toBe("zero_day");
    expect(attackMeta(null).label).toBe("unknown");
    expect(attackMeta(undefined).color).toBeTruthy();
  });
});

describe("confidencePercent", () => {
  it("formats probabilities as percentages", () => {
    expect(confidencePercent(0.964)).toBe("96.4%");
    expect(confidencePercent(1)).toBe("100.0%");
  });

  it("degrades on garbage", () => {
    expect(confidencePercent(undefined)).toBe("—");
    expect(confidencePercent("high")).toBe("—");
    expect(confidencePercent(NaN)).toBe("—");
  });
});

describe("timeOfDay", () => {
  it("extracts HH:MM:SS from the contract timestamp", () => {
    expect(timeOfDay("2026-08-26T17:43:08Z")).toBe("17:43:08");
  });

  it("degrades on malformed timestamps", () => {
    expect(timeOfDay(null)).toBe("—");
    expect(timeOfDay("yesterday")).toBe("—");
  });
});

describe("buildTypeChartData", () => {
  it("shapes attacks_by_type for the chart", () => {
    const rows = buildTypeChartData({ dos: 5, probe: 0, r2l: 1, u2r: 0 });
    expect(rows).toHaveLength(4);
    expect(rows[0]).toEqual(
      { type: "dos", label: "DoS", count: 5, color: attackMeta("dos").color });
  });

  it("keeps unexpected categories and survives null", () => {
    expect(buildTypeChartData({ worm: 2 })[0].label).toBe("worm");
    expect(buildTypeChartData(null)).toEqual([]);
  });
});

describe("buildTimelineData", () => {
  it("copies entries with numeric defaults", () => {
    expect(buildTimelineData([{ minute: "10:14", normal: 3, attack: 1 }]))
      .toEqual([{ minute: "10:14", normal: 3, attack: 1 }]);
    expect(buildTimelineData([{ minute: "10:15" }]))
      .toEqual([{ minute: "10:15", normal: 0, attack: 0 }]);
  });

  it("survives non-arrays", () => {
    expect(buildTimelineData(undefined)).toEqual([]);
  });
});

describe("sameRecord", () => {
  const record = {
    prediction: "attack", attack_type: "dos", confidence: 0.97,
    timestamp: "2026-08-26T10:00:00Z",
    features: { service: "http", src_bytes: 181 },
  };

  it("matches a fresh copy of the same record (new object after a poll)", () => {
    expect(sameRecord(record, structuredClone(record))).toBe(true);
  });

  it("distinguishes different records and survives null", () => {
    expect(sameRecord(record, { ...record, confidence: 0.5 })).toBe(false);
    expect(sameRecord(record, null)).toBe(false);
    expect(sameRecord(null, null)).toBe(false);
  });
});

describe("alertsFrom", () => {
  it("keeps only attack rows, preserving order", () => {
    const records = [
      { prediction: "attack", attack_type: "dos" },
      { prediction: "normal", attack_type: null },
      { prediction: "attack", attack_type: "r2l" },
    ];
    expect(alertsFrom(records).map((r) => r.attack_type))
      .toEqual(["dos", "r2l"]);
  });

  it("survives garbage rows and non-arrays", () => {
    expect(alertsFrom([null, {}, { prediction: "attack" }])).toHaveLength(1);
    expect(alertsFrom(undefined)).toEqual([]);
  });
});
