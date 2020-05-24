import { MissingTranslationHandler, MissingTranslationHandlerParams } from '@ngx-translate/core';
import { Observable, of } from 'rxjs';
import { catchError, map, shareReplay, take, tap } from 'rxjs/operators';

export class MyMissingTranslationHandler extends MissingTranslationHandler {
  // кушируем Observable с перевдом, т.к. при входе на страницу, для которой еще нет переводов
  // каждая translate pipe вызовет метод handle
  private translatesLoading: { [lang: string]: Observable<object> } = {};

  handle(params: MissingTranslationHandlerParams) {
    const service = params.translateService;
    const lang = service.currentLang || service.defaultLang;

    if (!this.translatesLoading[lang]) {
      // вызываем загрузку переводов через loader (тот самый, который реализован выше)
      this.translatesLoading[lang] = service.currentLoader.getTranslation(lang).pipe(
        // добавляем переводы в общее хранилище ngx-translate
        // флаг true говорит о том, что объекты необходимо смерджить
        tap(t => service.setTranslation(lang, t, true)),
        map(() => service.translations[lang]),
        shareReplay(1),
        take(1),
      );
    }

    return this.translatesLoading[lang].pipe(
      // вытаскиваем необходимый перевод по ключу и вставляем в него параметры
      map(t => service.parser.interpolate(service.parser.getValue(t, params.key), params.interpolateParams)),
      // при ошибке эмулируем стандарное поведение когда нет перевода - возвращаем ключ
      catchError(() => of(params.key)),
    );
  }
}
