import { render, screen } from "@testing-library/react";
import { PhoneLink } from "./PhoneLink";

describe("PhoneLink", () => {
  it("keeps the raw display value while using the canonical dial URI", () => {
    render(<PhoneLink value="070 123 45 67" dialUri="tel:+46701234567" />);

    const link = screen.getByRole("link", { name: "070 123 45 67" });
    expect(link).toHaveAttribute("href", "tel:+46701234567");
  });

  it("renders a legacy value without an unsafe link when canonical identity is missing", () => {
    render(<PhoneLink value="070 123 45 67" dialUri={null} />);

    expect(screen.getByText("070 123 45 67")).toBeInTheDocument();
    expect(screen.queryByRole("link")).not.toBeInTheDocument();
  });

  it("handles a missing phone without creating a link", () => {
    render(<PhoneLink value={null} dialUri={null} />);

    expect(screen.getByText("—")).toBeInTheDocument();
    expect(screen.queryByRole("link")).not.toBeInTheDocument();
  });
});
