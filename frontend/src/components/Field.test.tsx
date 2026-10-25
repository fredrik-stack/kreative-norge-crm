import { render, screen } from "@testing-library/react";
import { Field } from "./Field";

it("labels a nested input beside suggestions and preserves its description", () => {
  render(<Field label="Tags" name="tags" error="Rett feltet"><div><input aria-describedby="help"/><div><button>Forslag</button></div></div><small id="help">Hjelp</small></Field>);
  const input=screen.getByRole('textbox',{name:'Tags'});
  expect(input).toHaveAccessibleDescription('Hjelp Rett feltet');
  expect(input).toHaveAttribute('aria-invalid','true');
});
it("keeps individual names in a composite group",()=>{
  render(<Field label="Telefon"><div><select aria-label="Region"><option>Norge</option></select><input aria-label="Nummer"/></div></Field>);
  expect(screen.getByRole('combobox',{name:'Region'})).toBeInTheDocument();
  expect(screen.getByRole('textbox',{name:'Nummer'})).toBeInTheDocument();
});
