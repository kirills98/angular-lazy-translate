import { ChangeDetectionStrategy, Component } from '@angular/core';
import { TranslateService } from '@ngx-translate/core';

@Component({
  selector: 'app-root',
  templateUrl: './app.component.html',
  styles: [`
    .link {
        color: dodgerblue;
        cursor: pointer;
        text-decoration: none;
    }
    
    .link_active {
        text-decoration: underline;
        font-weight: 700;
    }
  `],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class AppComponent {
  constructor(private translateService: TranslateService) {
    translateService.use('ru');
  }

  changeLang(lang: string): void {
    this.translateService.use(lang);
  }

  checkLang(lang: string): boolean {
    return this.translateService.currentLang === lang;
  }
}
