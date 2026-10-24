import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { vi } from 'vitest';
import { ProfileFormActions } from './ProfileFormActions';
import { profileStatus } from '../editor-utils';

it('has exactly one form submit and blocks reset while saving', () => {
 const submit=vi.fn(e=>e.preventDefault()); const reset=vi.fn();
 const { rerender }=render(<form onSubmit={submit}><ProfileFormActions model="person" isNew={false} state="saving" dirty disabled={false} onReset={reset}/></form>);
 expect(screen.getByRole('button',{name:'Lagre person'})).toBeDisabled();
 fireEvent.click(screen.getByRole('button',{name:'Forkast profilutkast'}));
 expect(reset).not.toHaveBeenCalled();
 expect(document.querySelectorAll('button[type="submit"]')).toHaveLength(1);
 rerender(<form onSubmit={submit}><ProfileFormActions model="person" isNew={false} state="idle" dirty={false} disabled={false} onReset={reset}/></form>);
 fireEvent.click(screen.getByRole('button',{name:'Lagre person'}));
 expect(submit).toHaveBeenCalledTimes(1);
 expect(screen.getByRole('status')).toHaveTextContent('Ingen ulagrede profilfelt');
 expect(screen.queryByText(/Sist lagret/)).not.toBeInTheDocument();
});
it('prioritizes active request/error, then new edits over old saved',()=>{
 expect(profileStatus('saving',true,false,'person').label).toMatch(/Lagrer/);
 expect(profileStatus('error',true,false,'person').label).toBe('Lagring ikke bekreftet');
 expect(profileStatus('saved',true,false,'person').label).toBe('Ulagrede profilfelt');
 expect(profileStatus('saved',false,false,'person').label).toBe('Personskjema lagret');
 expect(profileStatus('idle',false,true,'person').label).toBe('Nytt profilutkast');
});

it('keeps a focused profile field above an overlapping sticky row after focus/resize', async () => {
 const { container }=render(<><input aria-label="Separate area"/><form><input aria-label="Profile field"/><ProfileFormActions model="person" isNew={false} state="idle" dirty={false} disabled={false} onReset={()=>{}}/></form></>);
 const field=screen.getByLabelText('Profile field');
 const outside=screen.getByLabelText('Separate area');
 const row=container.querySelector('.profile-form-actions') as HTMLElement;
 row.style.position='sticky';
 vi.spyOn(row,'getBoundingClientRect').mockReturnValue({top:700,bottom:850} as DOMRect);
 vi.spyOn(field,'getBoundingClientRect').mockReturnValue({top:740,bottom:780} as DOMRect);
 const scroll=vi.fn();Object.defineProperty(field,'scrollIntoView',{value:scroll,configurable:true});
 field.focus();await waitFor(()=>expect(scroll).toHaveBeenCalledWith({block:'center'}));
 scroll.mockClear();fireEvent(window,new Event('resize'));
 await waitFor(()=>expect(scroll).toHaveBeenCalledTimes(1));
 scroll.mockClear();outside.focus();fireEvent(window,new Event('resize'));
 await new Promise(resolve=>requestAnimationFrame(resolve));expect(scroll).not.toHaveBeenCalled();
 row.style.position='static';field.focus();fireEvent(window,new Event('resize'));
 await new Promise(resolve=>requestAnimationFrame(resolve));expect(scroll).not.toHaveBeenCalled();
});
