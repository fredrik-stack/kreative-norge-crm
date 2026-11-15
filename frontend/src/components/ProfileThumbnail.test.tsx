import { fireEvent, render, screen } from "@testing-library/react";
import { ProfileThumbnail } from "./ProfileThumbnail";

it("shows the full actor name when the authoritative projection is fallback, including with a valid generic URL", () => {
  const {container} = render(<ProfileThumbnail url="https://public.example/fallback.png" kind="system_fallback" name="Andøy jazzklubb" />);
  expect(screen.getByRole("img", {name: "Andøy jazzklubb"})).toHaveTextContent("Andøy jazzklubb");
  expect(container.querySelector("img")).toBeNull();
});

it("keeps approved asset and legacy images, falls back on load failure and retries a changed URL", () => {
  const {container, rerender} = render(<ProfileThumbnail url="/private/preview/1" kind="asset" name="Synthetic actor" />);
  fireEvent.error(container.querySelector("img")!);
  expect(screen.getByRole("img", {name: "Synthetic actor"})).toHaveTextContent("Synthetic actor");
  rerender(<ProfileThumbnail url="/private/preview/2" kind="asset" name="Synthetic actor" />);
  expect(container.querySelector("img")).toHaveAttribute("src", "/private/preview/2");
  rerender(<ProfileThumbnail url="https://legacy.example/image.png" name="Synthetic actor" />);
  expect(container.querySelector("img")).toHaveAttribute("src", "https://legacy.example/image.png");
});
