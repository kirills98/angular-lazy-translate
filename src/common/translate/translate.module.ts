import { HttpClient } from '@angular/common/http';
import { ModuleWithProviders, NgModule } from '@angular/core';
import {
  MissingTranslationHandler,
  TranslateLoader,
  TranslateModule,
  TranslateModuleConfig,
} from '@ngx-translate/core';

import { MyMissingTranslationHandler } from './missing-translation-handler';
import { MyTranslationLoader } from './translation-loader';

export function httpLoaderFactory(scopes: string | string[]): (http: HttpClient) => TranslateLoader {
  return (http: HttpClient) => new MyTranslationLoader(http, scopes);
}

export function translateConfig(scopes: string | string[]): TranslateModuleConfig {
  return {
    useDefaultLang: false,
    loader: {
      provide: TranslateLoader,
      useFactory: httpLoaderFactory(scopes),
      deps: [HttpClient],
    },
  };
}

@NgModule()
export class MyTranslateModule {
  static forRoot(scopes: string | string[] = [], config?: TranslateModuleConfig): ModuleWithProviders<TranslateModule> {
    return TranslateModule.forRoot({
      ...translateConfig([''].concat(scopes)),
      ...config,
    });
  }

  static forChild(scopes: string | string[], config?: TranslateModuleConfig): ModuleWithProviders<TranslateModule> {
    return TranslateModule.forChild({
      ...translateConfig(scopes),
      extend: true,
      missingTranslationHandler: {
        provide: MissingTranslationHandler,
        useClass: MyMissingTranslationHandler,
      },
      ...config,
    });
  }
}
