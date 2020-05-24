import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';

import { HomeComponent } from './home.component';
import { MyTranslateModule } from '../../common/translate';


@NgModule({
  imports: [
    CommonModule,
    RouterModule.forChild([{path: '', component: HomeComponent}]),
    MyTranslateModule.forChild(['HOME', 'HOME.COMMON'])
  ],
  declarations: [HomeComponent],
})
export class HomeModule {
}
