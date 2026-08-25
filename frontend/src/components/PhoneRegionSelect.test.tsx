import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { PhoneRegionSelect, initialPhoneRegion } from "./PhoneRegionSelect";

describe("PhoneRegionSelect", () => {
  it("allows an explicit region and an empty selection", async () => {
    const onChange = vi.fn();
    render(<PhoneRegionSelect value="" onChange={onChange} />);

    await userEvent.selectOptions(
      screen.getByRole("combobox", { name: "Land/region for telefonnummer" }),
      "SE",
    );
    expect(onChange).toHaveBeenCalledWith("SE");
    expect(screen.getByRole("option", { name: "Norge (NO)" })).toBeInTheDocument();
  });

  it("uses tenant default only for a national number", () => {
    expect(initialPhoneRegion("22 12 34 56", null, "NO")).toBe("NO");
    expect(initialPhoneRegion("+46 8 505 103 00", null, "NO")).toBe("");
  });

  it("prefers the region persisted for the concrete phone", () => {
    expect(initialPhoneRegion("08-505 103 00", "SE", "NO")).toBe("SE");
  });
});
