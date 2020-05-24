import { OnDestroy } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, of, zip } from 'rxjs';
import { map, tap } from 'rxjs/operators';
import { TranslateLoader } from '@ngx-translate/core';

export class MyTranslationLoader extends TranslateLoader implements OnDestroy {
  /** Глобальный кеш с флагами скачанных файлов переводов (что бы не качать их повторно, для разных модулей) */
  private static TRANSLATES_LOADED: { [lang: string]: { [scope: string]: boolean } } = {};

  /** Сортируем ключи по возрастанию длинны (маленькие куски будут вмердживаться в большие) */
  private sortedScopes = typeof this.scopes === 'string' ? [this.scopes] : this.scopes.slice().sort((a, b) => a.length - b.length);

  private getURL(lang: string, scope: string): string {
    // эта строка будет зависеть, от того, куда и как вы кладете файлы переводов
    // в нашем случае, они лежат в корне проекта в директории i18n
    return `i18n/${scope ? scope + '/' : ''}${lang}.json`;
  }

  /** Скачиваем переводы и запоминаем, что мы их скачали */
  private loadScope(lang: string, scope: string): Observable<object> {
    return this.httpClient.get(this.getURL(lang, scope)).pipe(
      tap(() => {
        if (!MyTranslationLoader.TRANSLATES_LOADED[lang]) {
          MyTranslationLoader.TRANSLATES_LOADED[lang] = {};
        }
        MyTranslationLoader.TRANSLATES_LOADED[lang][scope] = true;
      }),
    );
  }

  /**
   * Все скачанные переводы необходимо объеденить в один объект
   * т.к. мы знаем что файлы переводов не имеют пересечений по ключам,
   * можно вместо сложной логики глубокого мерджа, просто наложить объекты друг на друга
   * на надо делать это в правильном порядке, именно для этого мы выше отсортировали наши scope по длине
   * чтобы, наложить HOME.COMMON на HOME, а не наоборот
   */
  private merge(scope: string, source: object, target: object): object {
    // обрабатываем пустую строку для root модуля
    if (!scope) {
      return {...target};
    }

    const parts = scope.split('.');
    const scopeKey = parts.pop();
    const result = {...source};
    // рекурсивно получаем ссылку на объект в который необходимо добавить часть переводов
    const sourceObj = parts.reduce(
      (acc, key) => (acc[key] = typeof acc[key] === 'object' ? {...acc[key]} : {}),
      result,
    );
    // также рекурсивно достаем нужную часть переводов и присваиваем
    sourceObj[scopeKey] = parts.reduce((res, key) => res[key] || {}, target)?.[scopeKey] || {};

    return result;
  }

  constructor(private httpClient: HttpClient, private scopes: string | string[]) {
    super();
  }

  ngOnDestroy(): void {
    // сбрасываем кеш, что бы при hot reaload переводы перекачались
    MyTranslationLoader.TRANSLATES_LOADED = {};
  }

  getTranslation(lang: string): Observable<object> {
    // берем только еще не скачанные scope
    const loadScopes = this.sortedScopes.filter(s => !MyTranslationLoader.TRANSLATES_LOADED?.[lang]?.[s]);

    if (!loadScopes.length) {
      return of({});
    }

    // скачиваем все и сливаем в один объект
    return zip(...loadScopes.map(s => this.loadScope(lang, s))).pipe(
      map(translates => translates.reduce((acc, t, i) => this.merge(loadScopes[i], acc, t), {})),
    );
  }
}
