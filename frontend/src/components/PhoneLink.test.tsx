import { render, screen } from "@testing-library/react";
import { PhoneLink } from "./PhoneLink";

describe("PhoneLink", () => {
  it("keeps the raw display value while using the canonical dial URI", () => {
    render(
      <PhoneLink
        value="070 123 45 67"
        dialUri="tel:+46701234567"
        countryCallingCodeHint="46"
      />,
    );

    const link = screen.getByRole("link", { name: "070 123 45 67 (+46)" });
    expect(link).toHaveAttribute("href", "tel:+46701234567");
  });

  it("does not add a redundant hint for the tenant's own country", () => {
    render(<PhoneLink value="900 12 345" dialUri="tel:+4790012345" countryCallingCodeHint={null} />);

    expect(screen.getByRole("link", { name: "900 12 345" })).toHaveAttribute("href", "tel:+4790012345");
    expect(screen.queryByText("(+47)")).not.toBeInTheDocument();
  });

  it("does not duplicate a calling code already visible in an international value", () => {
    render(
      <PhoneLink
        value="+46 70 123 45 67"
        dialUri="tel:+46701234567"
        countryCallingCodeHint="46"
      />,
    );

    expect(screen.getByRole("link", { name: "+46 70 123 45 67" })).toHaveAttribute(
      "href",
      "tel:+46701234567",
    );
    expect(screen.queryByText("(+46)")).not.toBeInTheDocument();
  });

  it("renders calling-code metadata without country-specific frontend logic", () => {
    render(<PhoneLink value="20 12 34 56" dialUri="tel:+4520123456" countryCallingCodeHint="45" />);

    expect(screen.getByRole("link", { name: "20 12 34 56 (+45)" })).toHaveAttribute(
      "href",
      "tel:+4520123456",
    );
  });

  it("renders a legacy value without an unsafe link when canonical identity is missing", () => {
    render(<PhoneLink value="070 123 45 67" dialUri={null} countryCallingCodeHint="46" />);

    expect(screen.getByText(/070 123 45 67/)).toHaveTextContent("070 123 45 67 (+46)");
    expect(screen.queryByRole("link")).not.toBeInTheDocument();
  });

  it("handles a missing phone without creating a link", () => {
    render(<PhoneLink value={null} dialUri={null} />);

    expect(screen.getByText("—")).toBeInTheDocument();
    expect(screen.queryByRole("link")).not.toBeInTheDocument();
  });
});
