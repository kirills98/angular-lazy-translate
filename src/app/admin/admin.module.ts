import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';

import { AdminComponent } from './admin.component';
import { MyTranslateModule } from '../../common/translate';


@NgModule({
  imports: [
    CommonModule,
    RouterModule.forChild([{path: '', component: AdminComponent}]),
    MyTranslateModule.forChild(['ADMIN', 'HOME.COMMON'])
  ],
  declarations: [AdminComponent],
})
export class AdminModule {
}
